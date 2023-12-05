import sys, os
import numpy as np
import matplotlib.style
#matplotlib.style.use('classic')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

#def plotGeneratedFiles( _attenuation, _coherence_time, _mem_eff, _det_eff, _N, _saveFig ):

_saveFig = True
markers = [ 'o', '^', 's', 'P', 'd', 'p', '*' ]

plotOnly = 'syn' # 'syn', 'ind'

srcDir = 'data'
dstDir = 'plots'
_N = 1000000

vLight = 2e8
    
#_coherence_time_avg = 0.8e-3
#_coherence_time_stdev = 0. * _coherence_time_avg
_coherence_time_stdev = 0.2 * 0.1e-3
attenuation = 0.0002
mem_eff = 0.3 #9
det_eff = 0.8
swap_probability = 0.5
swap_degradation = 0.95
#_coharence_time = ( _coherence_time_avg, _coherence_time_stdev )

#_coherence_time_avg, _coherence_time_stdev = _coherence_time

msize = 7

plt.clf()
ax = plt.gca()

#_attenuation1 = 0.0
#_coherence_time_avg1 = _coherence_time_avg #-1

#print( 10**( 0.2 * 40 / -10.0 ) )

def entRateNoReps( _L, _att, _mem_eff, _det_eff ):
    _expFtr = 10**( _att * _L / -20.0 )
    _P_bsm1 = ( 0.5 * _mem_eff * _det_eff * _expFtr #* ( 1 - _mem_eff * _det_eff * _expFtr )
                #+ 2 *_mem_eff**2 * _det_eff * ( 1 - _det_eff ) * _expFtr**2
                )
    _P_bsm2 = 1.0 * _mem_eff * _det_eff * _expFtr
    #return (1/6.0) * vLight / _L * _det_eff**2 * _mem_eff**2 * _expFtr**2
    return (4 #+ _P_bsm1 - (1-_mem_eff)
            )**-1 * vLight / _L * _P_bsm1 * _P_bsm2

def entRateSyn( _L, _att, _mem_eff, _det_eff, _swap_succ_prob, _numReps ):
    return ( vLight / (2*_L) * _swap_succ_prob**_numReps / 2**( _numReps + 1 )
             * _mem_eff**( 2 * ( _numReps + 1 ) ) * _det_eff**( 2 * ( _numReps + 1 ) )
             * 10**( _att * _L / -10.0 ) )

def entRateInd( _L, _att, _mem_eff, _det_eff, _swap_succ_prob, _numReps ):
    #return ( vLight * (_numReps + 1) / _L * _swap_succ_prob**_numReps /
    #         ( 4*10**( _att * _L / ( _numReps + 1 ) / 10.0 )/(  _mem_eff**2 * _det_eff**2 )
    #           + _numReps ) )
    return ( vLight * np.sqrt( _numReps + 1 ) / (4*_L) * _swap_succ_prob**_numReps
             * _mem_eff**2 * _det_eff**2
             * 10**( _att * _L / ( _numReps + 1 ) / -10.0 ) )

Ls = np.arange( 1, 150.1, 0.2 )

print( 0.5 * mem_eff**2 * det_eff**2 * 10**( attenuation * Ls[len(Ls)//2]*1000/2 / -10.0 ) )
cts = np.array( [ [ 0.1, 0.1/5 ],
                  [ 0.2, 0.1/5 ],
                  [ 0.4, 0.1/5 ],
                  [ 0.6, 0.1/5 ],
                  [ 0.8, 0.1/5 ],
                  #[ 1.0, 0.1/5 ],
                  #[ -1000.0, 0. ]
                  ] ) * 1e-3
if plotOnly == 'syn' or plotOnly == '':
    for i in range( cts.shape[0] ):
        _attenuation1 = attenuation
        fname2 = ( 'entRateSyn(R=%d)(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,swEff=%.2f,N=1E%d).txt' 
                    % (
                         0,
                         _attenuation1 * 1000,
                         '%.3fms' % ( cts[i,0] / 1e-3 ) if cts[i,0] > 0.0 else 'inf',
                        ( '+-%.2fmcs,' % ( cts[i,1] / 1e-6 )
                           if ( cts[i,0] > 0 and cts[i,1] > 0 )
                           else ',' ),
                         mem_eff, det_eff, swap_probability, np.log10(_N) ) )
        data2 = np.loadtxt( srcDir + '/' + fname2 )
        reg2 = data2[ :, 1 ] > 0.0
        data2 = data2[ reg2, : ]

        #if i == 0:
        #    ents = entRateNoReps( Ls*1000, _attenuation1, mem_eff, det_eff )
        #    line, = ax.semilogy( Ls, ents, lw = 1 )
        ax.semilogy( data2[ :, 0 ]/1000, data2[ :, 1 ], lw = 3,#markers[i], #color = line.get_color(),
                     ms = msize, mec = 'none',
                    label = r'$\tau_\mathrm{mem}$ = %s' % ( r'%.1f$\pm$%.2f ms' % ( cts[i,0] / 1e-3, cts[i,1] / 1e-3 ) if cts[i,0] > 0.0 else r'$\infty$'#cts[i,0]/1e-3
                                                         ) )

    ents = entRateNoReps( Ls*1000, _attenuation1, mem_eff, det_eff )
    ax.semilogy( Ls, ents, 'k--', lw = 2, label = r'model, $\tau_\mathrm{mem}=\infty$' )

    ax.set_xlim( -2, 152 )
    ax.set_ylim( ( 1e-1, 2e4 ) )      

ax.xaxis.set_major_locator( MultipleLocator( 25 ) )
ax.xaxis.set_minor_locator( MultipleLocator( 5 ) )
        
#plt.loglog( [2*2e5*_coherence_time_avg,]*2, [1, 2.5e4], 'k--', lw = 1.5 )
plt.legend( loc = 1, fontsize = 14, frameon = False, numpoints = 1 )

ax.tick_params( axis='both', direction = 'in', which='major', labelsize=13 )
ax.tick_params( axis='both', direction = 'in', which='minor', labelsize=11 )

ax.tick_params( axis='x', direction = 'in', which='major', labelsize=13, top = True )
ax.tick_params( axis='x', direction = 'in', which='minor', labelsize=11, top = True )

ax.tick_params( axis='y', direction = 'in', which='major', labelsize=13, right = True )
ax.tick_params( axis='y', direction = 'in', which='minor', labelsize=11, right = True )
        
plt.xlabel( 'Distance, km', fontsize = 15 )
plt.ylabel( 'Entanglement gen. rate, 1/sec', fontsize = 15 )

#ax.annotate( '(b)', xy=( 0.05, 0.975 ), xycoords='axes fraction',
#                   fontsize=22,
#                   #fontweight='bold',
#                   horizontalalignment='left', verticalalignment='top' )
    
if _saveFig:
    if not os.path.isdir(dstDir):
        print( 'creating output directory' )
        os.mkdir(dstDir)
    plt.savefig( dstDir + '/' + 'fig1b.svg' )
plt.show()

    

