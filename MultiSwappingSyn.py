import sys, os, time
from math import inf
import multiprocessing as mp

from enum import Enum, auto

from sequence.topology.node import Node
from sequence.components.memory import MemoryWithRandomCoherenceTime
from sequence.entanglement_management.generation import EntanglementGenerationA, GenProtoStatus
from sequence.kernel.timeline import Timeline
from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.topology.node import BSMNode
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
from sequence.entanglement_management.swapping import EntanglementSwappingA, EntanglementSwappingB
from sequence.resource_management.resource_manager import ResourceManagerMessage, ResourceManagerMsgType
from sequence.message import Message

import logging
from sequence.utils import log

import numpy as np

doSimulations = False
doDubugOutput = False


class ControlNodeMsgType(Enum):
    #LINK_WAS_ESTABLISHED = auto()
    LINK_STATUS_UPDATED = auto()
    ESTABLISHED_LINK_WAS_BROKEN = auto()
    
class ControlNodeMessage(Message):
    def __init__(self, msg_type: ControlNodeMsgType, _origin: str, **kwargs ):
        Message.__init__(self, msg_type, "EntangleGenNode")
        self.origin = _origin
        if msg_type is ControlNodeMsgType.LINK_STATUS_UPDATED:
            self.established = kwargs[ 'established' ] if 'established' in kwargs else True
            pass
        else:
            raise Exception("ControlNodeMessage gets unknown type of message: %s" % str(msg_type))

class Link():
    def __init__( self, _nodesNos = None ):
        if not _nodesNos is None:
            assert _nodesNos[ 0 ] < _nodesNos[ 1 ]
            self.node_left = _nodesNos[ 0 ]
            self.node_right = _nodesNos[ 1 ]
        else:
            self.node_left = None
            self.node_right = None
            
        self.node_left_memo_updated = False
        self.node_right_memo_updated = False
        self.genProtocolFinished = False
        self.established = False
        self.memoryExpired = False
        
    def copy_from( self, _other ):
        self.node_left = _other.node_left
        self.node_right = _other.node_right
        self.node_left_memo_updated = _other.node_left_memo_updated
        self.node_right_memo_updated = _other.node_right_memo_updated
        self.genProtocolFinished = _other.genProtocolFinished
        self.established = _other.established
        self.memoryExpired = _other.memoryExpired
            
        return self
    
class ControlNodeData():
    def __init__( self ):
        self.genLinksUpdated = None
        self.genLinksEstablished = None
        self.numLinksToBeUpdatedAtThisSession = None

class SimpleManager():
    def __init__(self, _owner, _nodesTracker):
        self.owner = _owner
        self.nodeNo = int( _owner.name[4:] )
        self.leftMemoName = '%s.left_memo' % _owner.name
        self.rightMemoName = '%s.right_memo' % _owner.name
        self.nodesTracker = _nodesTracker
        #self.eg_updates = [ False, False ]
        #self.wasEntangled = [ False, False ]

    def update( self, protocol, memory, state ):
        if len( protocol.name ) < 3:
            raise ValueError( 'I don\'t know this protocol name: %s' % protocol.name )
            
        if protocol.name[ -3: ] == '_eg':
            self.update_eg( protocol, memory, state )
        elif protocol.name[ -3: ] == 'ESA':
            self.update_es( protocol, memory, state )
        else:
            if len( protocol.name ) < 4:
                raise ValueError( 'I don\'t know this protocol name: %s' % protocol.name )
            if protocol.name[-4] == 'G':
                self.update_eg( protocol, memory, state )
            elif protocol.name[-4] == 'S':
                self.update_es( protocol, memory, state )
            else:
                raise ValueError( 'Wrong protocol name: %s' % protocol.name )

    def update_eg( self, protocol, memory, state ):
        _memo_id = None
        if memory.name == self.leftMemoName:
            _memo_id = 0
            #self.updated[0] = True
        elif memory.name == self.rightMemoName:
            _memo_id = 1
            #self.updated[1] = True
        else:
            raise ValueError( 'I don\'t have another sides of a node' )
            
        #if self.nodesTracker.blockResourceManagerUpdating:
        #    return
        
        _nodes = self.nodesTracker.nodes
        #_memosToTrack = self.nodesTracker.memosToTrack
        _cnodeNo = self.nodesTracker.cnodeNo
        _numRouters = self.nodesTracker.numRouters
        
        #_lastProtoEvent = _nodes[2*self.nodeNo].isTheLastProtocolEvent(_memo_id)
        _protocol_status = self.owner.protocols[_memo_id].status
            
        #print( _memosToTrack, self.nodeNo, _memo_id )
        
        if doDubugOutput:
            print( 'protofol status:', str( _protocol_status ) )
            print( '########### UPDATE generation ###################' )
            print( 'memory state:', state, 'memory name:', memory.name )
            _time_now = self.nodesTracker.tl.now()
            print( 'time:', _time_now )
            #if _time_now == 301012510:
            #    print( 'Let\'s break here' )
            for j in range( 1, self.nodesTracker.numRouters + 2 ):
                print( _nodes[2*j].left_memo.entangled_memory,
                       _nodes[2*j-2].right_memo.entangled_memory )

        _found = None
        _remote_nodeNo = None
        
        for _i in range( len( self.nodesTracker.links ) ):
            _l = self.nodesTracker.links[ _i ]
            _found = False
            if _memo_id == 1 and self.nodeNo == _l.node_left:
                if ( _protocol_status is GenProtoStatus.ENDING or
                     _protocol_status is GenProtoStatus.MEMORY_EXPIRED ):#_lastProtoEvent:
                    if not _l.node_left_memo_updated:
                        _l.node_left_memo_updated = True
                        _found = True
                _remote_nodeNo = _l.node_right
            elif _memo_id == 0 and self.nodeNo == _l.node_right:
                if ( _protocol_status is GenProtoStatus.ENDING or
                     _protocol_status is GenProtoStatus.MEMORY_EXPIRED ):
                    if not _l.node_right_memo_updated:
                        _l.node_right_memo_updated = True
                        _found = True
                _remote_nodeNo = _l.node_left
            else:
                continue
            
            if _found:
                if _protocol_status is GenProtoStatus.MEMORY_EXPIRED:
                    #print( str( GenProtoStatus.MEMORY_EXPIRED ) )
                    if not _l.memoryExpired:
                        _l.memoryExpired = True
                
                #_linkWasUpdated = False
                _established = False
                #_updated_link = Link()
                #print( _updated_link.node_left_memo_updated, _updated_link.node_right_memo_updated )
                if _l.node_left_memo_updated and _l.node_right_memo_updated:
                    _node_right_name1 = _nodes[2*_l.node_left].right_memo.entangled_memory['node_id']
                    _node_left_name1 = _nodes[2*_l.node_right].left_memo.entangled_memory['node_id']
                    
                    if _node_right_name1 is None and _node_left_name1 is None:
                        #self.nodesTracker.numGeneratedLinksReported += 1
                        _l.genProtocolFinished = True
                    elif not ( _node_right_name1 is None or _node_left_name1 is None ):
                        #self.nodesTracker.numGeneratedLinksReported += 1
                        _l.genProtocolFinished = True
                        _l.established = True
                        _established = True
                        #raise ValueError( self.nodesTracker.links[ _i ].genProtocolFinished )
                        
                        ######### just doing more double checks ##################
                        if _memo_id == 1:
                            _remote_node_name1 = _nodes[2*self.nodeNo].right_memo.entangled_memory['node_id']
                        elif _memo_id == 0:
                            _remote_node_name1 = _nodes[2*self.nodeNo].left_memo.entangled_memory['node_id']
                        else:
                            raise ValueError( 'Wrong memory id: %d' % _memo_id 
                                             )
                        _remote_nodeNo1 = int( _remote_node_name1[4:] )
                        try:
                            assert _remote_nodeNo1 == _remote_nodeNo
                            if _memo_id == 0:
                                _node_name1 = _nodes[2*_remote_nodeNo].right_memo.entangled_memory['node_id']
                            elif _memo_id == 1:
                                _node_name1 = _nodes[2*_remote_nodeNo].left_memo.entangled_memory['node_id']
                            else:
                                raise ValueError( 'Wrong memory id: %d' % _memo_id )
                            
                            _nodeNo1 = int( _node_name1[4:] )
                            assert _nodeNo1 == self.nodeNo
                        except AssertionError as e:
                            print( 'link between:', _l.node_left, 'and', _l.node_right )
                            print( _nodes[2*self.nodeNo].right_memo.entangled_memory if _memo_id == 1
                                  else _nodes[2*self.nodeNo].right_memo.entangled_memory )
                            print( _nodes[2*_remote_nodeNo].left_memo.entangled_memory if _memo_it == 1
                                  else _nodes[2*_remote_nodeNo].right_memo.entangled_memory )
                            raise AssertionError( e )
                          
                        self.nodesTracker.establishedLinks.append( Link().copy_from( _l ) )
                        self.nodesTracker.links.pop(_i)
                        
                    #self.nodesTracker.numGeneratedLinksReported += 1
                    #                    
                    #_remote_node_name1 = _nodes[2*self.nodeNo].right_memo.entangled_memory['node_id']
                    #_established = False
                    #if not _remote_node_name1 is None:
                    #    _remote_nodeNo1 = int( _remote_node_name1[4:] )
                    #    assert _remote_nodeNo1 == _remote_nodeNo
                    #    _node_name1 = _nodes[2*_remote_nodeNo].right_memo.entangled_memory['node_id']
                    #    if not _node_name1 is None:
                    #        _nodeNo1 = int( _node_name1[4:] )
                    #        assert _nodeNo1 == self.nodeNo
                    #        _established = True
                    #
                    #        self.nodesTracker.establishedLinks.append( _l )
                    #        self.nodesTracker.links.pop(_i)
                    
                    #if _established:
                    #    srcNodeNo = None
                    #    if abs( self.nodeNo - self.nodesTracker.cnodeNo ) < abs( _remote_nodeNo - self.nodesTracker.cnodeNo ):
                    #        srcNodeNo = self.nodeNo
                    #    elif abs( self.nodeNo - self.nodesTracker.cnodeNo ) > abs( _remote_nodeNo - self.nodesTracker.cnodeNo ):
                    #        srcNodeNo = _remote_nodeNo
                    #    else:
                    #        raise ValueError( 'That can\'t happen' )
                    #        
                    #    msg = ControlNodeMessage( ControlNodeMsgType.LINK_WAS_ESTABLISHED, 'generation' )        
                    #    if srcNodeNo != self.nodesTracker.cnodeNo:
                    #        _nodes[2*srcNodeNo].send_message( _nodes[2*self.nodesTracker.cnodeNo].name, msg )
                    #    else:
                    #        self.owner.receive_message( self.owner.name, msg )
                    #    #print( 'established fuck you shit' )
                break
        
        if not _found:
            return
        
        ##_protocol_status = self.owner.protocols[_memo_id].status
        _updated_link = self.nodesTracker.establishedLinks[ -1 ] if _established else self.nodesTracker.links[ _i ]
        if _updated_link.genProtocolFinished:
            srcNodeNo = None
            assert ( _updated_link.node_left == self.nodeNo and _updated_link.node_right == _remote_nodeNo or
                    _updated_link.node_left == _remote_nodeNo and _updated_link.node_right == self.nodeNo )
            if abs( self.nodeNo - self.nodesTracker.cnodeNo ) < abs( _remote_nodeNo - self.nodesTracker.cnodeNo ):
                srcNodeNo = self.nodeNo
            elif abs( self.nodeNo - self.nodesTracker.cnodeNo ) > abs( _remote_nodeNo - self.nodesTracker.cnodeNo ):
                srcNodeNo = _remote_nodeNo
            else:
                raise ValueError( 'That can\'t happen' )
                            
            msg = ControlNodeMessage( ControlNodeMsgType.LINK_STATUS_UPDATED, 'generation', established = _updated_link.established )        
            if srcNodeNo != self.nodesTracker.cnodeNo:
                _nodes[2*srcNodeNo].send_message( _nodes[2*self.nodesTracker.cnodeNo].name, msg )
            else:
                self.nodesTracker.cnode.receive_message( _nodes[2*srcNodeNo].name, msg )
        #if ( _updated_link_ref.node_left_memo_updated and _updated_link_ref.node_right_memo_updated and
        #    self.nodesTracker.numGeneratedLinksReported == self.nodesTracker.numLinksToBeUpdatedAtThisSession ):
        #    _linksLeftToEstablish = len( self.nodesTracker.links )
        #    #print( 'linksLeftToEstablish', _linksLeftToEstablish )
        #    if _linksLeftToEstablish > 0:
        #        #self.nodesTracker.numLinksToBeUpdatedAtThisSession = len( self.nodesTracker.links )
        #        #self.nodesTracker.numGeneratedLinksReported = 0
        #        #self.nodesTracker.flushAllPendingEvents()
        #        for j in range( 1, _numRouters + 1 ):
        #            _nodes[2*j-2].protocols[1].status = GenProtoStatus.INITIALIZED
        #            _nodes[2*j].protocols[0].status = GenProtoStatus.INITIALIZED
        #        _have_expired_memories = False
        #        for _l in self.nodesTracker.links:
        #            if _l.memoryExpired == True:
        #                _have_expired_memories = True
        #                break
        #        _time_to_wait = ( 0.55 * self.nodesTracker.endnode_distance / self.nodesTracker.light_speed 
        #                         / ( self.nodesTracker.numRouters + 1 ) if _have_expired_memories else 1 ) 
        #                            # 0.5+ is because once 
        #                            #memory expired, it voids emitted photon, but if it had reached bsm node and the bsm 
        #                            #sent the measurements results, nobody voids that message, so we just have to wait 
        #                            #once it's delivered and ignored by resource_manager.update() due to the protocol's 
        #                            #state INITIALIZED
        #        
        #        self.nodesTracker.tl.schedule( Event( self.nodesTracker.tl.now() + _time_to_wait, 
        #                                             self.nodesTracker.process ) )
            
    def update_es( self, protocol, memory, state ):
        _memo_id = None
        if memory.name == self.leftMemoName:
            _memo_id = 0
            #self.updated[0] = True
        elif memory.name == self.rightMemoName:
            _memo_id = 1
            #self.updated[1] = True
            
        if state == 'RAW':
            memory.reset()
        #else:
        #    pass
        #    #memory.reset()
        
        #if self.nodesTracker.blockResourceManagerUpdating:
        #    return

        _nodes = self.nodesTracker.nodes
        #_memosToTrack = self.nodesTracker.memosToTrack
        #print( _memosToTrack, self.nodeNo, _memo_id )
        
        if doDubugOutput:
            print( '########### UPDATE swapping ###################' )
            print( 'memory state:', state, 'memory name:', memory.name )
            print( 'time:', self.nodesTracker.tl.now() )
            for j in range( 1, self.nodesTracker.numRouters + 2 ):
                print( _nodes[2*j].left_memo.entangled_memory,
                       _nodes[2*j-2].right_memo.entangled_memory )

        for _i in range( len( self.nodesTracker.links ) ):
            _l = self.nodesTracker.links[_i]
            _found = False
            if _memo_id == 1 and self.nodeNo == _l.node_left:
                if not _l.node_left_memo_updated:
                    _l.node_left_memo_updated = True
                _found = True
                _remote_nodeNo = _l.node_right
            elif _memo_id == 0 and self.nodeNo == _l.node_right:
                if not _l.node_right_memo_updated:
                    _l.node_right_memo_updated = True
                _found = True
                _remote_nodeNo = _l.node_left
            else:
                continue
            
            if _found:
                if _l.node_left_memo_updated and _l.node_right_memo_updated:
                    self.nodesTracker.links.pop( _i )
                    
                break

        if len( self.nodesTracker.links ) == 0: #and self.nodesTracker.tl.now() <= self.nodesTracker.lastButExpireEventTime:
            #self.nodesTracker.removeAllButExpirePendingEvents()
            self.nodesTracker.blockResourceManagerUpdating = True
            __wait_time = self.nodesTracker.signalingDelay + self.nodesTracker.swpAccDelayDelta + 1 #1.0*self.nodesTracker.endnode_distance/self.nodesTracker.light_speed
            self.nodesTracker.tl.schedule( Event( self.nodesTracker.tl.now() + __wait_time, self.nodesTracker.process ) )
            #print( 'dbg: swp protocol ended:',  self.nodesTracker.tl.now() * self.nodesTracker.light_speed / self.nodesTracker.endnode_distance )
            
    def release_remote_protocol(self, dst: str, protocol: "EntanglementProtocol") -> None:
        """Method to release protocols from memories on distant nodes.

        Release the remote protocol 'protocol' on the remote node 'dst'.
        The local protocol was paired with the remote protocol but local protocol becomes invalid.
        The resource manager needs to notify the remote node to cancel the paired protocol.

        Args:
            dst (str): name of the destination node.
            protocol (EntanglementProtocol): protocol to release on node.
        """

        msg = ResourceManagerMessage(ResourceManagerMsgType.RELEASE_PROTOCOL, protocol=protocol)
        #print( 'from:', self.owner.name, 'to:', self.nodesTracker.nodes[self.nodeNo].name )
        #[ print( ch ) for ch in self.owner.cchannels ]
    	#raise ValueError( 'Let\'s stop here' )
        self.owner.send_message(dst, msg)


class EntangleGenNode(Node):
    def __init__( self, _name: str, tl: Timeline, _nodesTracker, **memory_params ):
        super().__init__(_name, tl)
        #fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500 
        #self.memory = MemoryWithRandomCoherenceTime('%s.memo'%name, tl, **memory_params ) #0.9, 2000, 1, -1, 500)
        #self.memory.owner = self
        self.left_memo = MemoryWithRandomCoherenceTime('%s.left_memo' % _name,
                                                       tl, **memory_params ) #WithRandomCoherenceTime
        self.left_memo.owner = self
        self.left_memo.attach( self )
        self.right_memo = MemoryWithRandomCoherenceTime('%s.right_memo' % _name,
                                                        tl, **memory_params )
        self.right_memo.owner = self
        self.right_memo.attach( self )
        self.resource_manager = SimpleManager( self, _nodesTracker )
        self.protocols = [ None ] * 4
        self.cnodeData = None

    def receive_message( self, src: str, msg: "Message") -> None:
        msg_type = str( msg.msg_type )
        #print( msg_type )
        
        if len( msg_type ) >= 22: #ResourceManagerMsgType.RELEASE_PROTOCOL
            if msg_type[:22] == 'ResourceManagerMsgType':
                
                if msg.msg_type is ResourceManagerMsgType.RELEASE_PROTOCOL:
                    assert isinstance(msg.protocol, EntanglementProtocol)
                    #print( msg.msg_type, msg.protocol.name )
                    msg.protocol.release()
                    return
                elif msg.msg_type is ResourceManagerMsgType.RELEASE_MEMORY:
                    #print( msg.msg_type, msg.memory.name )
                    target_id = msg.memory
                    for p in self.protocols:
                        if not p is None:
                            for memory in p.memories:
                                if memory.name == target_id:
                                    p.release()
                    return
                else:
                    raise ValueError( 'I\'m not expecting this kind of messages: %s' % msg_type )
        
        if len( msg_type ) >= 17:
            if msg_type[:17] == 'GenerationMsgType':
                if len(src) > len( 'node' ): 
                    if src[:4] == 'node':
                        if int( src[4:] ) > int( self.name[4:] ):
                            self.protocols[1].received_message(src, msg)
                        elif int( src[4:] ) < int( self.name[4:] ):
                            self.protocols[0].received_message(src, msg)
                        else:
                            raise ValueError( 'Don\'t know what message has been received' )
                        return
                if len(src) > len( 'bsm_node' ):
                    if src[:8] == 'bsm_node':
                        if int( src[8:] ) > int( self.name[4:] ):
                            self.protocols[1].received_message(src, msg)
                        elif int( src[8:] ) == int( self.name[4:] ):
                            self.protocols[0].received_message(src, msg)
                        else:
                            raise ValueError( 'Don\'t know what message has been received' )
                        return
        
        if len( msg_type ) >= 15:
            if msg_type[:15] == 'SwappingMsgType':
                if len(src) > len( 'node' ): 
                    if src[:4] == 'node':
                        if int( src[4:] ) > int( self.name[4:] ):
                            self.protocols[3].received_message(src, msg)
                        elif int( src[4:] ) < int( self.name[4:] ):
                            self.protocols[2].received_message(src, msg)
                return
            
        if type( msg.msg_type ) is ControlNodeMsgType:
            if msg.msg_type is ControlNodeMsgType.LINK_STATUS_UPDATED:
                if msg.origin == 'generation':
                    _nodesTracker = self.resource_manager.nodesTracker
                    _nodes = _nodesTracker.nodes
                    _cnodeData = _nodesTracker.cnode.cnodeData
                    
                    _cnodeData.genLinksUpdated += 1
                    if msg.established:
                        _cnodeData.genLinksEstablished += 1
                    
                    if _cnodeData.genLinksUpdated == _cnodeData.numLinksToBeUpdatedAtThisSession:
                        if _cnodeData.genLinksEstablished == _nodesTracker.numRouters + 1:
                            _process = Process( _nodesTracker, 'doSwappingPart', [] )
                            _nodesTracker.updateProcessToSchedule( _process )
                            _nodesTracker.numLinksToBeUpdatedAtThisSession = None
                            _cnodeData.numLinksToBeUpdatedAtThisSession = None
                            #_nodesTracker.flushAllPendingEvents()
                            for j in range( 1, _nodesTracker.numRouters + 1 ):
                                _nodes[2*j-2].protocols[1].status = GenProtoStatus.INITIALIZED
                                _nodes[2*j].protocols[0].status = GenProtoStatus.INITIALIZED
                            #_nodesTracker.blockResourceManagerUpdating = True
                            _time_to_wait = ( _nodesTracker.signalingDelay + 1 #0.5*_nodesTracker.endnode_distance/_nodesTracker.light_speed
                                              if _nodesTracker.numRouters > 0
                                              else 1 )
                            _nodesTracker.tl.schedule( Event( _nodesTracker.tl.now() + _time_to_wait,
                                                              _process ) )
                            #print( 'dbg: cnode calls swapping:',  _nodesTracker.tl.now() * _nodesTracker.light_speed / _nodesTracker.endnode_distance )
                        else:
                            for j in range( 1, _nodesTracker.numRouters + 1 ):
                                _nodes[2*j-2].protocols[1].status = GenProtoStatus.INITIALIZED
                                _nodes[2*j].protocols[0].status = GenProtoStatus.INITIALIZED
                            #_nodesTracker.numGeneratedLinksReported = 0
                            _cnodeData.genLinksEstablished = 0
                            _cnodeData.genLinksUpdated = 0
                            _nodesTracker.resetAllMemories()
                            _nodesTracker.flushTotallyAllPendingEvents()
                            _nodesTracker.result = False
                            #print( 'dbg: cnode received gen failed:',  _nodesTracker.tl.now() * _nodesTracker.light_speed / _nodesTracker.endnode_distance )

            elif msg.msg_type is ControlNodeMsgType.ESTABLISHED_LINK_WAS_BROKEN:
                _nodesTracker = self.resource_manager.nodesTracker
                _nodesTracker.resetAllMemories()
                _nodesTracker.flushTotallyAllPendingEvents()
                _nodesTracker.resetNodesUpdatesFlags()
                _nodesTracker.result = False
            else:
                raise ValueError( 'I don\'t expext this msg_type: %s' % msg_type )
        else:
            raise ValueError( 'Don\'t know what message has been received:', msg_type, src )
            
    def lastScheduledEventTimeEG( self ):
        _time_l = None
        if not self.protocols[0] is None:
            _time_l = self.tl.now()
            for event in self.protocols[0].scheduled_events:
                if not event.is_removed:
                    if event.time > _time_l:
                        _time_l = event.time
        _time_r = None
        if not self.protocols[1] is None:
            _time_r = self.tl.now()
            for event in self.protocols[1].scheduled_events:
                if not event.is_removed:
                    if event.time > _time_r:
                        _time_r = event.time
        if _time_l is None and _time_r is None:
            return None
        elif _time_l is None:
            return _time_r
        elif _time_r is None:
            return _time_l
        else:
            return max( _time_l, _time_r )
        
    def isTheLastProtocolEvent( self, _memo_id ):
        _en = None
        for e in self.timeline.events:
            if not e.is_invalid():
                _en = e
                break
        if _en is None:
            return True
        
        _res = True
        for e in self.protocols[_memo_id].scheduled_events:
            if e >= _en:
                _res = False
                break
        return _res

    def create_eg_protocol( self, middle: str, other: str, memo_id: int ):
        if memo_id == 0:
            self.protocols[0] = EntanglementGenerationA(self, '%s.EGA.r'%self.name, middle, other, self.left_memo )
            #self.protocols = [EntanglementGenerationA(self, '%s.eg'%self.name, middle, other, self.left_memo )]
        elif memo_id == 1:
            self.protocols[1] = EntanglementGenerationA(self, '%s.EGA.l'%self.name, middle, other, self.right_memo )
            #self.protocols = [EntanglementGenerationA(self, '%s.eg'%self.name, middle, other, self.right_memo )]
        else:
            raise ValueError( 'Bad memory index: %d' % memo_id )

    def create_es_protocol_middle( self, _swapping_params ):
        self.protocols[2] = EntanglementSwappingA(self, '%s.ESA'%self.name, self.left_memo, self.right_memo, **_swapping_params)

    def create_es_protocol_ends( self, memo_id: int ):
        if memo_id == 0:
            self.protocols[2] = EntanglementSwappingB(self, '%s.ESB.r'%self.name, self.left_memo)
        elif memo_id == 1:
            self.protocols[3] = EntanglementSwappingB(self, '%s.ESB.l'%self.name, self.right_memo)
        else:
            raise ValueError( 'Bad memory index: %d' % memo_id )
            
    def memory_expire( self, memo ):
        posDot = memo.name.find( '.' )
        posDash = memo.name.find( '_' )
        __suffix = memo.name[ posDot+1:posDash ]
        if __suffix == 'left':
            mem_id = 0
        elif __suffix == 'right':
            mem_id = 1
        else:
            print( __suffix )
            raise ValueError( 'I don\'t know this name: %s' % memo.name )
        for p in self.protocols:
            if not p is None:
                if p.is_ready():

                    if len( p.name ) < 3:
                        raise ValueError( 'I don\'t know this protocol name: %s' % p.name )
                        
                    if p.name[ -3: ] == '_eg':
                        #self.update_eg( memory, state )
                        pass
                    elif p.name[ -3: ] == 'ESA':
                        p.memory_expire( memo )
                    else:
                        if len( p.name ) < 4:
                            raise ValueError( 'I don\'t know this protocol name: %s' % protocol.name )
                        if p.name[-4] == 'G':
                            if p.name[-1] == 'r' and mem_id == 0:
                                p.memory_expire( memo )
                            elif p.name[-1] == 'l' and mem_id == 1:
                                p.memory_expire( memo )
                            else:
                                pass
                                
                        elif p.name[-4] == 'S':
                            p.memory_expire( memo )
                        else:
                            raise ValueError( 'Wrong protocol name: %s' % protocol.name )

def pair_eg_protocol( p1: EntanglementProtocol, p2: EntanglementProtocol ):
    p1.set_others( p2 )
    p2.set_others( p1 )

def pair_es_protocol(p1, p2):
    p1.set_others(p2)
    p2.set_others(p1)

class NodesTracker():
    def __init__( self, _tl, _numRouters, _numGenerations, _light_speed, _endnode_distance ):
        self.tl = _tl
        self.numRouters = _numRouters
        self.cnodeNo = ( self.numRouters + 2 ) // 2
        self.N = _numGenerations
        self.light_speed = _light_speed
        self.endnode_distance = _endnode_distance
        self.genCounter = 0
        self.nodes = []
        self.swapping_params = None
        #self.memosToTrack = []
        self.links = []
        self.establishedLinks = []
        #self.numLinksToBeUpdatedAtThisSession = None
        self.numTrials = 0
        #self.lastButExpireEventTime = inf
        #self.numGeneratedLinksReported = 0
        self.process = None
        self.result = None
        #self.blockResourceManagerUpdating = True
        self.swpAccDelayDelta = 0
        self.signalingDelay = ( max( self.cnodeNo, _numRouters + 1 - self.cnodeNo )
                                * _endnode_distance / _light_speed / ( _numRouters + 1 ) ) 

    def reset( self ):
        #self.memosToTrack.clear()
        #self.entangledMemories.clear()
        self.links.clear()
        #self.numLinksToBeUpdatedAtThisSession = None
        #self.numGeneratedLinksReported = 0
        #self.lastButExpireEventTime = inf
        self.numTrials = 0
        self.process = None
        self.result = None
        
    #def resetNodesUpdatesFlags( self ):    
    #    for j in range( self.numRouters + 2 ):
    #       _eg_updates = self.nodes[2*j].resource_manager.eg_updates
    #       _eg_updates[0] = False
    #       _eg_updates[1] = False
        
    def setNodesList( self, _nodes ):
        self.nodes = _nodes
        self.cnode = self.nodes[ 2*self.cnodeNo ]
        self.cnode.cnodeData = ControlNodeData()

    def setSwappingParams( self, _swapping_params ):
        self.swapping_params = _swapping_params

    #def updateTrackingList( self, _memosToTrack ):
    #    self.memosToTrack = _memosToTrack
    #    self.memosToTrackCopy = list( _memosToTrack )

    def updateLinksToEstablish( self, _links ):
        self.links = _links
        self.establishedLinks.clear()
        #self.numLinksToBeUpdatedAtThisSession = len( _links )
        #self.cnode.cnodeData.numLinksToBeUpdatedAtThisSession = len( _links )

    def updateProcessToSchedule( self, _process ):
        self.process = _process

    def checkPathIsConsistent( s ):
        #print( '-----------------------------------------------' )
        #for j in range( 1, s.numRouters + 2 ):
        #    print( s.nodes[2*j-2].right_memo.entangled_memory, '\n',
        #           s.nodes[2*j].left_memo.entangled_memory )
        
        _numHoppings = 0
        _leftNodeNo = 0
        
        while True:
            _rightNodeName = s.nodes[2*_leftNodeNo].right_memo.entangled_memory['node_id']
            if _rightNodeName is None:
                break
            _rightNodeNo = int( _rightNodeName[4:] )
            
            _leftNodeNamePrev = s.nodes[2*_rightNodeNo].left_memo.entangled_memory['node_id']
            if _leftNodeNamePrev is None:
                break
            else:
                if int( _leftNodeNamePrev[4:] ) != _leftNodeNo:
                    break
                
            _numHoppings += 1
            _leftNodeNo = _rightNodeNo

        #print( _numHoppings if _leftNodeNo == s.numRouters + 1 else None )

        return _numHoppings if _leftNodeNo == s.numRouters + 1 else None

    #def resetEntangledMemories( self ):
    #    #for _m in self.entangledMemories:
    #    #    if _m[1] == 0:
    #    #        self.nodes[_m[0]].left_memo.reset()
    #    #    elif _m[1] == 1:
    #    #        self.nodes[_m[0]].right_memo.reset()
    #    #    else:
    #    #        raise ValueError( 'Wrong memo_id: %d' % _m[1] )
    #    #self.entangledMemories.clear()

    def resetAllMemories( self ):
        for j in range( 1, self.numRouters + 2 ):
            self.nodes[ 2*j-2 ].right_memo.reset()
            self.nodes[ 2*j ].left_memo.reset()
        for e in self.tl.events:
            if e.time >= self.tl.now() and not e.is_invalid():
                self.tl.remove_event( e )

    def resetUsedMemory( self ):
        for _m in self.memosToTrackCopy:
            if _m[1] == 0:
                self.nodes[2*_m[0]].left_memo.reset()
            elif _m[1] == 1:
                self.nodes[2*_m[0]].right_memo.reset()
            else:
                raise ValueError( 'Wrong memo_id: %d' % _m[1] )

    #def flushAllPendingEvents( s ):
    #    _numRemoved = 0
    #    for j in range( 1, s.numRouters ):
    #        for event in s.nodes[2*j-2].protocols[1].scheduled_events:
    #            if not event.is_invalid():
    #                s.tl.remove_event( event )
    #                _numRemoved += 1
    #        for event in s.nodes[2*j].protocols[0].scheduled_events:
    #            if not event.is_invalid():
    #                s.tl.remove_event( event )
    #                _numRemoved += 1
    #    #print( 'numRemoved:', _numRemoved )
        
    def flushTotallyAllPendingEvents( s ):
        _now = s.tl.now()
        for e in s.tl.events:
            if not e.is_invalid() and e.time >= _now:
                s.tl.remove_event( e )

    def doGenerationPart( s ):            
        if s.numTrials > 1e6:
            s.result = False
            s.resetAllMemories()
            s.flushTotallyAllPendingEvents()
            print( 'max iteration reached' )
            return

        if s.genCounter > s.N or s.tl.now() > 1160e12:
            s.resetAllMemories()
            s.result = False
            s.flushTotallyAllPendingEvents()
            return
            
        s.numTrials += 1

        if doDubugOutput:
            print( '################ generation ###################' )
            print( 'time:', s.tl.now() )
            for j in range( 1, s.numRouters + 2 ):
                print( s.nodes[2*j].left_memo.entangled_memory,
                       s.nodes[2*j-2].right_memo.entangled_memory )



        #print( s.links )

        if len( s.links ) == 0:
            #_process = Process( s, 'doSwappingPart', [] )
            #s.updateProcessToSchedule( _process )
            #s.tl.schedule( Event( s.tl.now() + 10, _process ) )
            return

        #_memosToTrack = []
        for _link in s.links:
            _j1, _j2 = _link.node_left, _link.node_right
            s.nodes[2*_j1].create_eg_protocol( s.nodes[2*_j1+1].name, s.nodes[2*_j2].name, 1 )
            s.nodes[2*_j2].create_eg_protocol( s.nodes[2*_j1+1].name, s.nodes[2*_j1].name, 0 )
            #_memosToTrack += [ ( _j1, 1 ), ( _j2, 0 ), ]
            _link.node_left_memo_updated = False
            _link.node_right_memo_updated = False
            _link.established = False
            _link.genProtocolFinished = False
            _link.memoryExpired = False
            
            #print( 'now pairing:', nodes[2*j-2].name, nodes[2*j-1].name, nodes[2*j].name )
            pair_eg_protocol( s.nodes[2*_j1].protocols[1], s.nodes[2*_j2].protocols[0] )

            #nodes[2*j-2].right_memo.reset()
            #nodes[2*j].left_memo.reset()

        #s.updateTrackingList( _memosToTrack )
        #s.numLinksToBeUpdatedAtThisSession = len( s.links )
        #s.numGeneratedLinksReported = 0
        s.nodes[ 2*s.cnodeNo ].cnodeData.numLinksToBeUpdatedAtThisSession = len( s.links )
        s.nodes[ 2*s.cnodeNo ].cnodeData.genLinksUpdated = 0

        s.tl.init()
            
        for _link in s.links:
            _j1, _j2 = _link.node_left, _link.node_right
            s.nodes[2*_j1].protocols[1].start()
            s.nodes[2*_j2].protocols[0].start()
            
        #s.blockResourceManagerUpdating = False

        s.genCounter += len( s.links )
        #s.updateProcessToSchedule( Process( s, 'doGenerationPart', [] ) )
        #print( 'dbg: gen_attemt_start:',  s.tl.now() * s.light_speed / s.endnode_distance )
        

    def doSwappingPart( s ):   
        if doDubugOutput:
            print( '################# swapping ###################' )
            print( 'time:', s.tl.now() )
            for j in range( 1, s.numRouters + 2 ):
                print( s.nodes[2*j].left_memo.entangled_memory,
                       s.nodes[2*j-2].right_memo.entangled_memory )
        _numHoppings = s.checkPathIsConsistent()
        #print( 'dbg: swapping iteration begin:',  s.tl.now() * s.light_speed / s.endnode_distance )
        #print( _numHoppings )
        if _numHoppings is None:
            #print( 'doSwappingPart returns False' )
            s.result = False
            s.resetAllMemories()
            s.flushTotallyAllPendingEvents()
            #s.resetUsedMemory()
            #print( 'dbg: no need swapping, FAILED' )
            return

        if _numHoppings == 1:
            #print( 'doSwappingPart returns True' )
            s.result = True
            s.resetAllMemories()
            s.flushTotallyAllPendingEvents()
            #s.resetUsedMemory()
            #print( 'dbg: no need swapping any more, ENTANGLED' )
            return

        leftNodeNo = 0
        entangledNodeName = s.nodes[0].right_memo.entangled_memory['node_id']
        midNodeNo = entangledNodeNo = int( entangledNodeName[4:] )

        s.establishedLinks.clear()
        s.links = []
        _success2 = True
        
        s.swpAccDelayDelta = 0.0
        __elemLinkLengthDelay = s.endnode_distance / ( s.numRouters + 1 ) / s.light_speed
        
        while True:
            rightNodeName = s.nodes[2*midNodeNo].right_memo.entangled_memory['node_id']
            if rightNodeName is None:
                print( 'wtf1' )
                _success2 = False
                break
            rightNodeNo = int( rightNodeName[4:] )

            s.nodes[2*leftNodeNo].protocols[ 3 ] = None
            s.nodes[2*rightNodeNo].protocols[ 2 ] = None
            s.nodes[2*midNodeNo].protocols[ 2:4 ] = [ None, None ]
            s.nodes[2*leftNodeNo].create_es_protocol_ends( 1 )
            s.nodes[2*rightNodeNo].create_es_protocol_ends( 0 )
            s.nodes[2*midNodeNo].create_es_protocol_middle( s.swapping_params )

            s.links.append( Link( ( leftNodeNo, rightNodeNo ) ) )            
            #memosToTrack += [ ( leftNodeNo, 1 ), ( rightNodeNo, 0 ),
            #                  #( midNodeNo, 0 ), ( midNodeNo, 1 ),
            #                  ]

            pair_es_protocol(s.nodes[2*leftNodeNo].protocols[3], s.nodes[2*midNodeNo].protocols[2])
            pair_es_protocol(s.nodes[2*rightNodeNo].protocols[2], s.nodes[2*midNodeNo].protocols[2])

            if leftNodeNo <= s.cnodeNo and rightNodeNo >= s.cnodeNo:
                pass
            elif abs( s.cnodeNo - leftNodeNo ) < abs( s.cnodeNo - rightNodeNo ):
                __extraDelayNeeded = abs( s.cnodeNo - leftNodeNo ) * __elemLinkLengthDelay
                if __extraDelayNeeded > s.swpAccDelayDelta:
                    s.swpAccDelayDelta = __extraDelayNeeded
            elif abs( s.cnodeNo - rightNodeNo ) < abs( s.cnodeNo - leftNodeNo ):
                __extraDelayNeeded = abs( s.cnodeNo - rightNodeNo ) * __elemLinkLengthDelay
                if __extraDelayNeeded > s.swpAccDelayDelta:
                    s.swpAccDelayDelta = __extraDelayNeeded
            else:
                raise ValueError( 'leftNode=%d, midNode=%d, rightNode=%d, cnodeNo=%d' % (
                    leftNodeNo, midNodeNo, rightNodeNo, s.cnodeNo ) )                    

            if rightNodeNo == s.numRouters + 1:
                break
                    
            midNodeName = s.nodes[2*rightNodeNo].right_memo.entangled_memory['node_id']
            if midNodeName is None:
                print( 'wtf2' )
                _success2 = False
                break
            midNodeNo = int( midNodeName[4:] )
            if midNodeNo == s.numRouters + 1:
                break

            leftNodeNo = rightNodeNo
                    
            continue

        if not _success2:
            raise ValueError( 'I expected path is consistent' )

        #s.updateTrackingList( memosToTrack )
                
        #s.tl.init()

        leftNodeNo = 0
        midNodeNo = entangledNodeNo
        while True:
            rightNodeName = s.nodes[2*midNodeNo].right_memo.entangled_memory['node_id']
            rightNodeNo = int( rightNodeName[4:] )

            #print( 'left/mid/right:', leftNodeNo, midNodeNo, rightNodeNo )
            #print( 'left:', s.nodes[2*leftNodeNo].protocols[ 2:4 ] )
            #print( 'right:', s.nodes[2*rightNodeNo].protocols[ 2:4 ] )
            #print( 'mid:', s.nodes[2*midNodeNo].protocols[ 2:4 ] )
            s.nodes[2*leftNodeNo].protocols[3].start()
            s.nodes[2*rightNodeNo].protocols[2].start()
            s.nodes[2*midNodeNo].protocols[2].start()

            if rightNodeNo == s.numRouters + 1:
                break
                    
            midNodeName = s.nodes[2*rightNodeNo].right_memo.entangled_memory['node_id']
            midNodeNo = int( midNodeName[4:] )
            if midNodeNo == s.numRouters + 1:
                break

            leftNodeNo = rightNodeNo
                    
            continue

        #s.entangledMemories = list( memosToTrack )

        #s.updateProcessToSchedule( Process( s, 'doSwappingPart', [] ) )
        #s.blockResourceManagerUpdating = False
        
        #s.lastButExpireEventTime = s.getLastButExpireEventTime()
        #print( s.lastButExpireEventTime )
        
    #def getLastButExpireEventTime( self ):
    #    #i = len( self.tl.events ) - 1
    #    #while True:
    #    #    if i < 0:
    #    #        break
    #    #    if self.tl.events[i].process.activation != 'expire':
    #    #        break
    #    #return self.tl.events[i].time if i >= 0 else inf
    #    res = None
    #    for e in reversed( self.tl.events ):
    #        if e.process.activation != 'expire':
    #            res = e.time
    #            break
    #    return res if not res is None else inf
            
    #def removeAllButExpirePendingEvents( self ):
    #    for e in self.tl.events:
    #        if not e.is_invalid() and e.time >= self.tl.now():
    #            if e.process.activation != 'expire':
    #                self.tl.remove_event( e )
            
def runSimulations( _numRouters, _distance, _light_speed, _memory_params, _detector_params, _qchannel_params, _swapping_params, _repetitions ):
    #__seed = 2 #int( time.time() * 1000 ) % 2**32
    #np.random.seed( __seed )
    _t0 = time.time()
    tl = Timeline()
    tl.init()
    #tl.seed( __seed )

    #log.set_logger( 'msi', tl, logfile = 'msi-1000ms1.txt' )
    #log.set_logger_level( 'DEBUG' )
    #log.track_module( 'swapping' )
    #log.track_module( 'memory' )
    #log.track_module( 'detector' )
    #log.track_module( 'bsm' )
    #log.track_module( 'node' )
    #log.track_module( 'timeline' )
    #log.track_module( 'generation' )
    #log.track_module( 'entanglement_protocol' )
    #log.track_module( 'optical_channel' )
    
    nodesTracker = NodesTracker( tl, _numRouters, _repetitions, _light_speed, _distance )

    _fiberPieceLength = _distance / ( 2 * ( _numRouters + 1 ) )
    #print( 'fiber piece length:', _fiberPieceLength )

    nodes = [ EntangleGenNode( 'node0', tl, nodesTracker, **_memory_params ) ]
    for i in range( 1, _numRouters + 2 ):
        nodei = EntangleGenNode( 'node%d' % i, tl, nodesTracker, **_memory_params )
        bsmNodei = BSMNode( 'bsm_node%d' % i , tl, [ nodes[-1].name, nodei.name ] )
        #print( nodes[-1].name, nodei.name )

        for name, param in _detector_params.items():
            bsmNodei.bsm.update_detectors_params( name, param )
        
        _qchannel_params[ "distance" ] = _fiberPieceLength
        
        qc1 = QuantumChannel( 'qc%dr' % ( i - 1 ), tl, **_qchannel_params, light_speed = _light_speed )
        qc2 = QuantumChannel( 'qc%dl' % i, tl, **_qchannel_params, light_speed = _light_speed )
        qc1.set_ends( nodes[-1], bsmNodei )
        qc2.set_ends( nodei, bsmNodei )

        nodes += [ bsmNodei, nodei ]
    
    for i in range( len( nodes ) ):
        for j in range( len( nodes ) ):
            if i == j:
                continue
            cc = ClassicalChannel( 'cc_%s_%s' % (nodes[i].name, nodes[j].name),
                                   tl, abs(i-j)*_fiberPieceLength, delay=-1,light_speed= _light_speed )
            cc.set_ends( nodes[i], nodes[j] )

    nodesTracker.setNodesList( nodes )
    nodesTracker.setSwappingParams( _swapping_params )
    
    #[ print( ch ) for ch in nodes[8].cchannels ]
    #raise ValueError( 'Let\'s stop here' )

    numSuccessCases = 0
    #memosToTrack = []
    links = []

    while nodesTracker.genCounter <= _repetitions:
    #for i in range( _repetitions ):

        nodesTracker.reset()
        #nodesTracker.updatedLinks = []
        nodesTracker.cnode.cnodeData.genLinksEstablished = 0
        assert len( links ) == 0
        links.clear()
        for j in range( 1, _numRouters + 2 ):
            links.append( Link( ( j-1, j ) ) )

        nodesTracker.updateLinksToEstablish( links )
        #nodesTracker.establishedLinks.clear()
        
        process = Process( nodesTracker, 'doGenerationPart', [] )
        nodesTracker.updateProcessToSchedule( process )
        #nodesTracker.blockResourceManagerUpdating = True
        #_time_to_wait = ( _distance / _light_speed *
        #                  ( 1.0 if nodesTracker.genCounter > 0 else 0.5 ) )
        _time_to_wait = nodesTracker.signalingDelay + 1 #( _distance / _light_speed *
        #                  ( 0.5 if _numRouters > 0 else 1.0 ) )
        tl.schedule( Event( tl.now() + _time_to_wait, process ) )

        tl.init()
        _time_start_virt = tl.now()
        #print( 'dbg: start', _time_start_virt * _light_speed / _distance )
        tl.run()

        _time_end_virt = tl.now()
        #print( 'dbg: difference', ( _time_end_virt - _time_start_virt ) * _light_speed / _distance )
        #print( nodesTracker.result )
        if nodesTracker.result:
            numSuccessCases += 1
            #print( 'result: %6.0f' % ( numSuccessCases / tl.now() * 1e12 ), 
            #      'counter: %7d' % nodesTracker.genCounter,
            #      'trials: %6d' % nodesTracker.numTrials,
            #      'time: %5.3f ms' % ( tl.now() / 1e9 ) )

            #print( '##############################################' )
            #for j in range( 1, _numRouters + 2 ):
            #    print( nodes[2*j-2].right_memo.entangled_memory, '\n',
            #           nodes[2*j].left_memo.entangled_memory )

            #break
            
        #if nodesTracker.genCounter > 25:
        #    break

        if tl.now() > 1160e12:
            break
    
    print( '%.0f km is calculated in %.3f s' % ( _distance/1e3, time.time() - _t0 ) )
    return numSuccessCases / tl.now() * 1e12

def runSimulationsProc( _numRouters, _distance, _light_speed, _memory_params, _detector_params, _qchannel_params, _swapping_params, _repetitions, _i ):
    return ( _i,
             runSimulations( _numRouters, _distance, _light_speed, _memory_params, _detector_params, _qchannel_params, _swapping_params, _repetitions ), )

def calculate( _numRouters, _max_distance_km, _distance_step_km, _light_speed, _attenuation, _coherence_time,
                   _mem_eff, _det_eff, _swap_probability, _swap_degradation, _N, **kwargs ):
    if not type(_coherence_time) is tuple:
        raise ValueError( 'input coherence_time must be tuple(2)' )

    _numCoresToUse = kwargs['num_cores_to_use'] if 'num_cores_to_use' in kwargs else 1

    _coherence_time_avg, _coherence_time_stdev = _coherence_time 

    #Ls = np.array( [ 20e3 ] )

    Ls = np.concatenate( ( np.array( [ 1 ] ),
                           np.arange( _distance_step_km if _distance_step_km > 1.0 else ( 1.0 + _distance_step_km ),
                                      _max_distance_km + 0.5 * _distance_step_km,
                                      _distance_step_km ) ) ) * 1e3
        
    print( 'coherence time = %.3f ms%s' % ( _coherence_time_avg / 1e-3,
                                            ( ' +- %.2fmcs' % ( _coherence_time_stdev / 1e-6 )
                                                if _coherence_time_avg > 0 and _coherence_time_stdev > 0.0 else '' ) ) )
    memory_params = { "fidelity": 0.9, "frequency": 2e6, "efficiency": _mem_eff,
                      "coherence_time": _coherence_time_avg,
                      "coherence_time_stdev": _coherence_time_stdev,
                      "wavelength": 500 }
    detector_params = { "efficiency": _det_eff, 
                        #"dark_count": 10, 
                        "time_resolution": 150, 
                        "count_rate": 50e7 
                        }
    qchannel_params = { "attenuation": _attenuation, 
                        "polarization_fidelity": 1.0, 
                        "distance": 0 }
    swapping_params = { "success_prob": _swap_probability,
                        "degradation": _swap_degradation }
    _t0 = time.time()

    __owerwrite = True
    
    dstDir = 'data'
    
    if not os.path.isdir(dstDir):
        print( 'creating output directory' )
        os.mkdir(dstDir)
    
    fname = ( 'entRateSyn(R=%d)(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,swEff=%.2f,N=1E%d).txt' 
                % ( _numRouters,
                    _attenuation * 1000,
                    '%.3fms' % ( _coherence_time_avg / 1e-3 ) if _coherence_time_avg > 0.0 else 'inf',
                    ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                    if ( _coherence_time_avg > 0 and _coherence_time_stdev > 0 )
                    else ',' ),
                    _mem_eff, _det_eff, _swap_probability, np.log10(_N) ) )
    
    if not __owerwrite:
        if os.path.isfile( dstDir + '/' + fname ):
            print( 'Already calculated:\n%s\nskipping' % fname )
            return
    
    if _numCoresToUse > 1:
        pool = mp.Pool( min( Ls.shape[0], _numCoresToUse ) ) 
    #numCpu = min( mp.cpu_count() - 4, self.hs.shape[0], 70 )

    rs = np.zeros( Ls.shape )
    result_objects = []
    
    for i in range( Ls.shape[0] ):
        result_objects.append( pool.apply_async( runSimulationsProc, args =( _numRouters, Ls[i], _light_speed, memory_params,
                                                                         detector_params, qchannel_params,
                                                                         swapping_params, _N, i ) )
                               if _numCoresToUse > 1
                               else runSimulationsProc( _numRouters, Ls[i], _light_speed, memory_params, detector_params,
                                                    qchannel_params, swapping_params, _N, i )
                               )
        #break
    
    print( 'numRouters = %d' % _numRouters )
    for _r in result_objects:
        _res_i = _r.get() if _numCoresToUse > 1 else _r
        rs[ _res_i[0] ] = _res_i[1]
        
    #for i in range( len( Ls ) ):    
    #    print( 'L = %.0f km' % ( Ls[i]/1000 ), 'rate =', rs[i] )

    if _numCoresToUse > 1:    
        pool.close()
        pool.join()
    
    #print( rs[0] )
    #return
        
    #for i in range( len( Ls ) ):
    #    rs[i] = runSimulations( _numRouters, Ls[i], memory_params, detector_params, qchannel_params, swapping_params, _N )
            
    print( 'Total calculation time is %.3f seconds' % ( time.time() - _t0 ) )
        

    np.savetxt( dstDir + '/' + fname, np.concatenate( ( Ls.reshape( (Ls.shape[0],1) ),
                                        rs.reshape( (Ls.shape[0],1) ) ), axis = 1 ) )

def plotGeneratedFiles( _attenuation, _coherence_time, _mem_eff, _det_eff, _N, _saveFig ):
    import matplotlib.style
    matplotlib.style.use('classic')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    if not type(_coherence_time) is tuple:
        raise ValueError( 'input coherence_time must be tuple(2)' )

    _coherence_time_avg, _coherence_time_stdev = _coherence_time 

    plt.clf()
    ax = plt.gca()

    #_attenuation1 = 0.0
    #_coherence_time_avg1 = -1
    #fname1 = ( 'entRate(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).txt' 
    #            % ( 
    #                _attenuation1 * 1000,
    #                 '%.3fms' % ( _coherence_time_avg1 / 1e-3 ) if _coherence_time_avg1 > 0.0 else 'inf',
    #                 ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
    #                   if ( _coherence_time_avg1 > 0 and _coherence_time_stdev > 0 )
    #                   else ',' ),
    #                 _mem_eff, _det_eff, np.log10(_N) ) )
    #data1 = np.loadtxt( fname1 )
    #reg1 = data1[ :, 1 ] > 0.0
    #data1 = data1[ reg1, : ]

    #plt.loglog( data1[ :, 0 ]/1000, data1[ :, 1 ], '.', ms = 20,#mec = 'none',
    #            label = r'$\alpha$ = %.1f, $t_\mathrm{coh}$ = $\infty$' % ( _attenuation1 / 1e-3 ) )

    for _numRouters in range( 9 ):
        _attenuation1 = _attenuation
        fname2 = ( 'entRateSyn(R=%d)(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).txt' 
                     % (
                         _numRouters,
                         _attenuation1 * 1000,
                         '%.3fms' % ( _coherence_time_avg1 / 1e-3 ) if _coherence_time_avg1 > 0.0 else 'inf',
                         ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                           if ( _coherence_time_avg1 > 0 and _coherence_time_stdev > 0 )
                           else ',' ),
                         _mem_eff, _det_eff, np.log10(_N) ) )
        data2 = np.loadtxt( fname2 )
        reg2 = data2[ :, 1 ] > 0.0
        data2 = data2[ reg2, : ]

        plt.semilogy( data2[ :, 0 ]/1000, data2[ :, 1 ], '.', ms = 10,#mec = 'none',
                    label = 'R = %d' % ( _numRouters ) )
        
    #plt.loglog( [2*2e5*_coherence_time_avg,]*2, [1, 2.5e4], 'k--', lw = 1.5 )
    plt.legend( loc = 1, fontsize = 16, frameon = False, numpoints = 1 )
    plt.xlim( -2, 502 )
    plt.ylim( 1e-0, 5e4 )

    ax.tick_params( axis='both', which='major', labelsize=13 )
    ax.tick_params( axis='both', which='minor', labelsize=11 )
        
    plt.xlabel( 'Distance, km', fontsize = 15 )
    plt.ylabel( 'Entanglement gen. rate, 1/sec', fontsize = 15 )
    
    if _saveFig:
        plt.savefig(
            ( 'entRateSyn(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).pdf' 
                 % ( 0.2,
                     '%.3fms' % ( _coherence_time_avg / 1e-3 ) if _coherence_time_avg > 0.0 else 'inf',
                     ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                       if ( _coherence_time_avg > 0  and _coherence_time_stdev > 0  )
                       else ',' ),
                     _mem_eff, _det_eff, np.log10(_N) ) )
            )
    plt.show()

class InputParameters():
    def __init__( self, _max_distance_km = None, _distance_step_km = None, _light_speed = None, _attenuation = None, _coherence_time_avg = None, 
                 _coherence_time_stdev = None, _mem_eff = None, _det_eff = None, _swap_probability = None, 
                 _swap_degradation = None, _N = None, _numRepeaters = 0, _num_cores_to_use = 1 ):
        self.max_distance_km = _max_distance_km
        self.distance_step_km = _distance_step_km
        self.light_speed = _light_speed 
        self.attenuation = _attenuation 
        self.coherence_time_avg = _coherence_time_avg 
        self.coherence_time_stdev = _coherence_time_stdev
        self.mem_eff = _mem_eff 
        self.det_eff = _det_eff 
        self.swap_probability = _swap_probability 
        self.swap_degradation = _swap_degradation 
        self.N = _N
        self.numRepeaters = _numRepeaters 
        self.num_cores_to_use = _num_cores_to_use
        
    def copy_from( self, _other ):
        self.max_distance_km = _other.max_distance_km
        self.distance_step_km = _other.distance_step_km
        self.light_speed = _other.light_speed 
        self.attenuation = _other.attenuation 
        self.coherence_time_avg = _other.coherence_time_avg 
        self.coherence_time_stdev = _other.coherence_time_stdev
        self.mem_eff = _other.mem_eff 
        self.det_eff = _other.det_eff 
        self.swap_probability = _other.swap_probability 
        self.swap_degradation = _other.swap_degradation 
        self.N = _other.N
        self.numRepeaters = _other.numRepeaters 
        self.num_cores_to_use = _other.num_cores_to_use
        
        return self
        

if doSimulations:
    N = 100000000
    #print( ControlNodeMsgType.I_AM_DONE )
    #print( isinstance( ControlNodeMsgType.I_AM_DONE, ControlNodeMsgType ) )
    #raise ValueError( 'Let\'s stop here' )
    
    __seed = 2 #int( time.time() * 1000 ) % 2**32
    np.random.seed( __seed )
    
    generateFiles = True
    plotFiles = False
    
    coherence_time_avg = 0.1e-3
    coherence_time_stdev = 0.2 * coherence_time_avg
    attenuation = 0.0002
    mem_eff = 0.9 #3
    det_eff = 0.8
    swap_probability = 0.5
    swap_degradation = 0.95
    #maxNumRepeaters = 2
    max_distance_km = 8
    distance_step_km = 0.1*8.0/6
    light_speed = 2e-4
    numCoresToUsee = 1 #90
    
    pars0 = InputParameters( max_distance_km, distance_step_km, light_speed, attenuation, coherence_time_avg, coherence_time_stdev,
                           mem_eff, det_eff, swap_probability, swap_degradation, N, 0, numCoresToUsee )
    
    #pars1 = InputParameters()
    #pars1.copy_from( pars0 )
    pl = [ pars0 ]
    
    #pl.append( InputParameters().copy_from( pl[-1] ) )
    #pl[-1].coherence_time_avg = 0.2e-3
    #pl[-1].max_distance_km = 50
    #pl[-1].distance_step_km = 1.0
    
    #pl.append( InputParameters().copy_from( pl[-1] ) )
    #pl[-1].coherence_time_avg = 0.4e-3
    #pl[-1].max_distance_km = 80
    #pl[-1].distance_step_km = 1.0

    pl.append( InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = 0.5e-3
    pl[-1].max_distance_km = 20
    pl[-1].distance_step_km = 1.0/3
    
    #pl.append( InputParameters().copy_from( pl[-1] ) )
    #pl[-1].coherence_time_avg = 0.6e-3
    #pl[-1].max_distance_km = 130
    #pl[-1].distance_step_km = 1.0

    #pl.append( InputParameters().copy_from( pl[-1] ) )
    #pl[-1].coherence_time_avg = 0.8e-3
    #pl[-1].distance_step_km = 1.0
    #pl[-1].max_distance_km = 160
    
    pl.append( InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = 1.0e-3
    pl[-1].max_distance_km = 28
    pl[-1].distance_step_km = 0.5

    #pl.append( InputParameters().copy_from( pl[-1] ) )
    #pl[-1].coherence_time_avg = -1
    #pl[-1].distance_step_km = 5.0
    #pl[-1].coherence_time_stdev = 0
    #pl[-1].max_distance_km = 152

    _t0 = time.time()
    if generateFiles:
        for ps in pl:
            for _numRepeaters in [ 1, 2, 3,
                                   4
                                   ]:#range( 0, 8 ):
                #[ 0, 1, 3, 7 ]:
                calculate( _numRepeaters, ps.max_distance_km, ps.distance_step_km, ps.light_speed, ps.attenuation,
                               ( ps.coherence_time_avg, ps.coherence_time_stdev ),
                               ps.mem_eff, ps.det_eff, ps.swap_probability, ps.swap_degradation, ps.N, 
                               num_cores_to_use = ps.num_cores_to_use )
    print( 'Total calculation time: %.3f secs' % ( time.time() - _t0 ) )
    if plotFiles:
        plotGeneratedFiles( attenuation,
                            ( coherence_time_avg, coherence_time_stdev ),
                            mem_eff, det_eff, N, True )

    

