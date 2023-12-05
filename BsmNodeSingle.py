import sys, time
sys.path.append( '../' )

from sequence.topology.node import Node
from sequence.components.memory import Memory #WithRandomCoherenceTime
from sequence.entanglement_management.generation import EntanglementGenerationA
from sequence.kernel.timeline import Timeline
from sequence.topology.node import BSMNode
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol

#import logging
#from sequence.utils import log

import numpy as np

doSimulations = True

class SimpleManager():
    def __init__(self, own, memo_name):
        #added 2 lines
        self.own = own
        self.memo_name = memo_name
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, protocol, memory, state):
        if state == 'RAW':
            self.raw_counter += 1
            memory.reset()
        else:
            self.ent_counter += 1
            memory.reset()
    #changed according to the Documentation
    def create_protocol(self, middle: str, other: str):
        self.own.protocols = [EntanglementGenerationA(self.own,
                                                  '%s.eg'%self.own.name,
                                                  middle, other,
                                                  self.own.components[self.memo_name])]

class EntangleGenNode(Node):
    def __init__(self, name: str, tl: Timeline, **memory_params ):
        super().__init__(name, tl)
        #fidelity=0.9, frequency=2000, efficiency=1, coherence_time=-1, wavelength=500 
        #changed this according to documentation example
        memory = Memory('%s.memo'%name, tl, **memory_params ) #0.9, 2000, 1, -1, 500) #WithRandomCoherenceTime
        memory.owner = self
        memory.add_receiver(self)
        self.add_component(memory)
        self.resource_manager = SimpleManager( self, memory.name )
        self.protocols = []

    def init(self):
        memory = self.get_components_by_type("Memory")[0]
        memory.reset()

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)

    def get(self, photon, **kwargs):
        self.send_qubit(kwargs['dst'], photon)



#oldversion
#def pair_protocol( p1: EntanglementProtocol, p2: EntanglementProtocol ):
#    p1.set_others( p2 )
#    p2.set_others( p1 )
#newversion
def pair_protocol(node1: Node, node2: Node):
    p1 = node1.protocols[0]
    p2 = node2.protocols[0]
    node1_memo_name = node1.get_components_by_type("Memory")[0].name
    node2_memo_name = node2.get_components_by_type("Memory")[0].name
    p1.set_others(p2.name, node2.name, [node2_memo_name])
    p2.set_others(p1.name, node1.name, [node1_memo_name])
    
def runSimulations( _distance, _memory_params, _detector_params, _qchannel_params, _repetitions ):
    __seed = 2#int( time.time() * 1000 ) % 2**32
    np.random.seed( __seed )
    
    tl = Timeline()
    tl.init()
    #tl.seed( __seed )
    
    #light_velocity = 2e8 #m/s
    #log.set_logger( 'bsm', tl, logfile = 'bsm0.txt' )
    #log.set_logger_level( 'DEBUG' )
    #log.track_module( 'swapping' )
    #log.track_module( 'memory' )
    #log.track_module( 'node' )
    #log.track_module( 'timeline' )
    #log.track_module( 'generation' )
    #log.track_module( 'entanglement_protocol' )

    node1 = EntangleGenNode( 'node1', tl, **_memory_params )
    node2 = EntangleGenNode( 'node2', tl, **_memory_params )
    bsm_node = BSMNode('bsm_node', tl, ['node1', 'node2'])

    node1.resource_manager.create_protocol('bsm_node', 'node2')
    node2.resource_manager.create_protocol('bsm_node', 'node1')
    pair_protocol(node1, node2)
    
    for name, param in _detector_params.items():
        #oldversion:
        #bsm_node.bsm.update_detectors_params( name, param )
        #newversion: (see Documentation chapter 3: Entanglement management)
        bsm_node.get_components_by_type("SingleAtomBSM")[0].update_detectors_params( name, param )
        #bob.update_detector_params(i, name, param)
    #bsm_node.bsm.update_detectors_params( 'efficiency', 1 )
    
    _qchannel_params[ "distance" ] = _distance/2
    #print( 'fiber piece length:', _distance/2 )
    
    qc1 = QuantumChannel( 'qc1', tl, **_qchannel_params )
    qc2 = QuantumChannel( 'qc2', tl, **_qchannel_params )
    #changed according to the Documentation Chapter 3
    qc1.set_ends(node1, bsm_node.name)
    qc2.set_ends(node2, bsm_node.name)
    
    nodes = [ node1, bsm_node, node2 ]
    
    for i in range(3):
        for j in range(3):
            #if i == j:
            #    continue
            #oldversion
            #cc = ClassicalChannel( 'cc_%s_%s' % (nodes[i].name, nodes[j].name),
            #                       tl, abs(i-j)*_distance/(len(nodes)-1), -1, 2e-4 )
            #newversion
            cc = ClassicalChannel( 'cc_%s_%s' % (nodes[i].name, nodes[j].name),
                                   tl, abs(i-j)*_distance/(len(nodes)-1), 2e-4 )
            cc.set_ends( nodes[i], nodes[j].name )

    #changed: moved outside the loop
    tl.init()
    #print( 'tl.now() = %.3f ms' % ( tl.now() / 1e9 ) )
    for i in range( _repetitions ):
        print( "repetition #", i + 1 )
        #tl.time = tl.now() + 1e11

        node1.resource_manager.create_protocol('bsm_node', 'node2')
        node2.resource_manager.create_protocol('bsm_node', 'node1')
        #oldversion
        #pair_protocol(node1.protocols[0], node2.protocols[0])
        #newversion
        pair_protocol(node1, node2)

        tl.init()

        node1.protocols[0].start()
        node2.protocols[0].start()
        _time_start_virt = tl.now()
        print( _time_start_virt )
        tl.run()

        #print( 'tl.now() = %.3f ms' % ( tl.now() / 1e9 ) )
        #_time_end_virt = tl.now()
        #print( ( _time_end_virt - _time_start_virt ) * 2e-4 / _distance )
        print(node1.resource_manager.ent_counter, ':', node1.resource_manager.raw_counter)
    #print( 'tl.now() = %.3f ms' % ( tl.now() / 1e9 ) )

    #print(node1.resource_manager.ent_counter, ':', node1.resource_manager.raw_counter)
    # (around 500:500; the exact number depends on the seed of numpy.random)
    #fidelities = np.array( node1.resource_manager.fidelities )
    #numPts = fidelities.shape[0]
    #xSum = np.sum( fidelities )
    #xxSum = np.sum( fidelities**2 )
    #xAvg = xSum / numPts
    #xStDev = np.sqrt( abs( xxSum / numPts - xAvg**2 ) )
    #print( 'Average fidelity: %f\n fidelity st dev: %f' % ( xAvg, xStDev ) )
    return node1.resource_manager.ent_counter / tl.now() * 1e12

def doSimulationNoRepeater( _attenuation, _max_distance_km, _coherence_time, _mem_eff, _det_eff, _N ):
    if not type(_coherence_time) is tuple:
        raise ValueError( 'input coherence_time must be tuple(2)' )

    _coherence_time_avg, _coherence_time_stdev = _coherence_time 

    #Ls = np.array( [ 20e3 ] )
    #Ls = np.arange( 1, 101, 2 ) * 1e3
    Ls = np.concatenate( ( np.array( [ 1 ] ),
                           np.arange( 10, _max_distance_km + 1, 10 ) ) ) * 1e3
        
    print( 'coherence time = %.3f ms%s' % ( _coherence_time_avg / 1e-3,
                                            ( ' +- %.2fmcs' % ( _coherence_time_stdev / 1e-6 )
                                                if _coherence_time_avg > 0 and _coherence_time_stdev > 0.0 else '' ) ) )
    memory_params = { "fidelity": 1.0, "frequency": 2e6, "efficiency": _mem_eff,
                        "coherence_time": _coherence_time_avg,
                        #"coherence_time_stdev": _coherence_time_stdev,
                      "wavelength": 500 }
    detector_params = { "efficiency": _det_eff, 
                        #"dark_count": 10, 
                        "time_resolution": 150, 
                        "count_rate": 50e7 
                        }
    qchannel_params = { "attenuation": _attenuation, 
                        "polarization_fidelity": 1.0, 
                        "distance": 0,
                        "light_speed": 2e-4 }
    _t0 = time.time()
        
    rs = np.zeros( Ls.shape )
    for i in range( len( Ls ) ):
        rs[i] = runSimulations( Ls[i], memory_params, detector_params, qchannel_params, _N )
        #break

    #print( rs[0] )
    #return
    print( 'Calculated in %.3f seconds' % ( time.time() - _t0 ) )
        
    #print( 'entanglements per second generated: %.3f' % etngs_per_sec )
    #print( rs )
    fname = ( 'entRate(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).txt' 
                % ( _attenuation * 1000,
                    '%.3fms' % ( _coherence_time_avg / 1e-3 ) if _coherence_time_avg > 0.0 else 'inf',
                    ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                    if ( _coherence_time_avg > 0 and _coherence_time_stdev > 0 )
                    else ',' ),
                    _mem_eff, _det_eff, np.log10(_N) ) )
    np.savetxt( fname, np.concatenate( ( Ls.reshape( (Ls.shape[0],1) ),
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

    _attenuation1 = 0.0
    _coherence_time_avg1 = -1
    fname1 = ( 'entRate(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).txt' 
                % ( 
                    _attenuation1 * 1000,
                     '%.3fms' % ( _coherence_time_avg1 / 1e-3 ) if _coherence_time_avg1 > 0.0 else 'inf',
                     ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                       if ( _coherence_time_avg1 > 0 and _coherence_time_stdev > 0 )
                       else ',' ),
                     _mem_eff, _det_eff, np.log10(_N) ) )
    data1 = np.loadtxt( fname1 )
    reg1 = data1[ :, 1 ] > 0.0
    data1 = data1[ reg1, : ]

    plt.semilogy( data1[ :, 0 ]/1000, data1[ :, 1 ], '.', ms = 20,#mec = 'none',
                label = r'$\alpha$ = %.1f, $t_\mathrm{coh}$ = $\infty$' % ( _attenuation1 / 1e-3 ) )

    _attenuation1 = _attenuation
    fname2 = ( 'entRate(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).txt' 
                 % ( 
                     _attenuation1 * 1000,
                     '%.3fms' % ( _coherence_time_avg1 / 1e-3 ) if _coherence_time_avg1 > 0.0 else 'inf',
                     ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                       if ( _coherence_time_avg1 > 0 and _coherence_time_stdev > 0 )
                       else ',' ),
                     _mem_eff, _det_eff, np.log10(_N) ) )
    data2 = np.loadtxt( fname2 )
    reg2 = data2[ :, 1 ] > 0.0
    data2 = data2[ reg2, : ]

    plt.semilogy( data2[ :, 0 ]/1000, data2[ :, 1 ], '.', ms = 20,#mec = 'none',
                label = r'$\alpha$ = %.1f dB/km, $t_\mathrm{coh}$ = $\infty$' % ( _attenuation1 * 1000 ) )

    _coherence_time_avg1 = _coherence_time_avg
    _attenuation1 = 0.0
    fname3 = ( 'entRate(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).txt' 
                 % ( 
                     _attenuation1 * 1000,
                     '%.3fms' % ( _coherence_time_avg1 / 1e-3 ) if _coherence_time_avg1 > 0.0 else 'inf',
                     ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                       if ( _coherence_time_avg1 > 0 and _coherence_time_stdev > 0 )
                       else ',' ),
                     _mem_eff, _det_eff, np.log10(_N) ) )
    data3 = np.loadtxt( fname3 )
    reg3 = data3[ :, 1 ] > 0.0
    data3 = data3[ reg3, : ]

    plt.semilogy( data3[ :, 0 ]/1000, data3[ :, 1 ], '.', ms = 10,#mec = 'none',
                    label = r'$\alpha$ = %.1f, $t_\mathrm{coh}$ = %s' % (
                        _attenuation1 * 1000,
                        r'%s%s' % ( '%.0f' % ( _coherence_time_avg1 / 1e-6 )
                                     if _coherence_time_avg1 > 0 else '\infty',
                                     ( ' $\pm$ %.0f mcs' % ( _coherence_time_stdev / 1e-6 )
                                       if ( _coherence_time_avg1 > 0 and _coherence_time_stdev > 0  )
                                       else ' mcs' ) ) ) )

    _attenuation1 = _attenuation
    fname4 = ( 'entRate(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).txt' 
                 % ( 
                     _attenuation1 * 1000,
                     '%.3fms' % ( _coherence_time_avg1 / 1e-3 ) if _coherence_time_avg1 > 0.0 else 'inf',
                     ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                       if ( _coherence_time_avg1 > 0 and _coherence_time_stdev > 0 )
                       else ',' ),
                     _mem_eff, _det_eff, np.log10(_N) ) )
    data4 = np.loadtxt( fname4 )
    reg4 = data4[ :, 1 ] > 0.0
    data4 = data4[ reg4, : ]

    plt.semilogy( data4[ :, 0 ]/1000, data4[ :, 1 ], '.', ms = 10,#mec = 'none',
                      label = r'$\alpha$ = %.1f dB/km, $t_\mathrm{coh}$ = %s' % (
                          0.2,
                          r'%s%s' % ( '%.0f' % ( _coherence_time_avg / 1e-6 )
                                     if _coherence_time_avg > 0 else '\infty',
                                     ( ' $\pm$ %.0f mcs' % ( _coherence_time_stdev / 1e-6 )
                                       if ( _coherence_time_avg > 0 and _coherence_time_stdev > 0  )
                                       else ' mcs' ) ) ) )
        
    plt.semilogy( [2*2e5*_coherence_time_avg,]*2, [1, 2.5e4], 'k--', lw = 1.5 )
    plt.legend( loc = 1, fontsize = 16, frameon = False, numpoints = 1 )
    plt.xlim( 1, 102 )
    plt.ylim( 1, 2.5e4 )

    ax.tick_params( axis='both', which='major', labelsize=13 )
    ax.tick_params( axis='both', which='minor', labelsize=11 )
        
    plt.xlabel( 'Distance, km', fontsize = 15 )
    plt.ylabel( 'Entanglement gen. rate, 1/sec', fontsize = 15 )
    
    if _saveFig:
        plt.savefig(
            ( 'entRate(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,N=1E%d).pdf' 
                 % ( 0.2,
                     '%.3fms' % ( _coherence_time_avg / 1e-3 ) if _coherence_time_avg > 0.0 else 'inf',
                     ( '+-%.2fmcs,' % ( _coherence_time_stdev / 1e-6 )
                       if ( _coherence_time_avg > 0  and _coherence_time_stdev > 0  )
                       else ',' ),
                     _mem_eff, _det_eff, np.log10(_N) ) )
            )
    plt.show()

if doSimulations:
    __N = 1000

    generateFiles = True
    plotFiles = False
    
    __coherence_time_avg = 0.1e-3
    __coherence_time_stdev = 0.2 * __coherence_time_avg
    __attenuation = 0.0002
    __mem_eff = 0.9
    __det_eff = 0.8
    max_distance_km = 500

    if generateFiles:
        """
        doSimulationNoRepeater( 0.0,
                                ( 0.0, __coherence_time_stdev ),
                                __mem_eff, __det_eff, __N )
        doSimulationNoRepeater( __attenuation,
                                ( 0.0, __coherence_time_stdev ),
                                __mem_eff, __det_eff, __N )
        doSimulationNoRepeater( 0.0,
                                ( __coherence_time_avg, 0.0 ),
                                __mem_eff, __det_eff, __N )
        """
        doSimulationNoRepeater( __attenuation, max_distance_km,
                                ( __coherence_time_avg, __coherence_time_stdev ),
                                __mem_eff, __det_eff, __N )
        """
        doSimulationNoRepeater( 0.0,
                                ( __coherence_time_avg, __coherence_time_stdev ),
                                __mem_eff, __det_eff, __N )
        doSimulationNoRepeater( __attenuation,
                                ( __coherence_time_avg, __coherence_time_stdev ),
                                __mem_eff, __det_eff, __N )
        """

    if plotFiles:
        plotGeneratedFiles( __attenuation,
                            ( __coherence_time_avg, __coherence_time_stdev ),
                            __mem_eff, __det_eff, __N, True )

    

