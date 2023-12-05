import sys, os
import numpy as np
import matplotlib.style
#matplotlib.style.use('classic')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

#def plotGeneratedFiles( _attenuation, _coherence_time, _mem_eff, _det_eff, _N, _saveFig ):

_saveFig = True

showPanelIds = True

srcDir = 'data'
dstDir = 'plots'
_N = 1000000

vLight = 2e8
    
_coherence_time_avg = 0.5e-3
#_coherence_time_stdev = 0. * _coherence_time_avg
_coherence_time_stdev = 0.2 * 0.1e-3
attenuation = 0.0002
mem_eff = 0.3 #3 #9
det_eff = 0.8 #3 #8
swap_probability = 0.5 #9 #5
swap_degradation = 0.95
#_coharence_time = ( _coherence_time_avg, _coherence_time_stdev )

#_coherence_time_avg, _coherence_time_stdev = _coherence_time

msize = 7

memTimes = ( ( 10e-3, 0.9 ),
             ( 100e-3, 0.9 ),
             ( 500e-3, 0.9 ),
             ( 500e-3, 0.3 ) )

panelIds = ( '(a)', '(b)', '(c)', '(d)' )

def entRateNoReps( _L, _att, _mem_eff, _det_eff ):
    return 0.25 * vLight / _L * _mem_eff**2 * _det_eff**2 * 10**( _att * _L / -10.0 )

def entRateSyn( _L, _att, _mem_eff, _det_eff, _swap_succ_prob, _numReps ):
    return ( vLight / (2*_L) * _swap_succ_prob**_numReps / 2**( _numReps + 1 )
             * _mem_eff**( 2 * ( _numReps + 1 ) ) * _det_eff**( 2 * ( _numReps + 1 ) )
             * 10**( _att * _L / -10.0 ) )

def entRateInd( _L, _att, _mem_eff, _det_eff, _swap_succ_prob, _numReps ):
    ##return ( vLight * (_numReps + 1) / _L * _swap_succ_prob**_numReps /
    ##         ( 4*10**( _att * _L / ( _numReps + 1 ) / 10.0 )/(  _mem_eff**2 * _det_eff**2 )
    ##           + _numReps ) )
    #return ( vLight * (1/np.sqrt( _numReps + 1 ) + 1 )**-1/ (2*_L) * _swap_succ_prob**_numReps
    #         * _mem_eff**2 * _det_eff**2
    #         * 10**( _att * _L / ( _numReps + 1 ) / -10.0 ) )
    _expFtr = 10**( _att * _L / ( -20.0 * ( _numReps + 1 ) ) )
    _P_bsm1 = ( 0.5 * _mem_eff * _det_eff * _expFtr #* ( 1 - _mem_eff * _det_eff * _expFtr )
                #+ 2 *_mem_eff**2 * _det_eff * ( 1 - _det_eff ) * _expFtr**2
                )
    _P_bsm2 = 1.0 * _mem_eff * _det_eff * _expFtr

    return ( vLight * ( 3.0/np.sqrt( _numReps + 1 ) )**-1/ (_L) * _swap_succ_prob**_numReps
             * ( _P_bsm1 * _P_bsm2 ) )
    #return ( 3.0 / np.sqrt( _numReps + 1 ) / ( _swap_succ_prob**_numReps
    #         * ( _P_bsm1 * _P_bsm2 ) ) + 1.0 + np.sqrt( _numReps + 1 ) )**-1 * vLight/_L


plt.clf()
ax = plt.gca()

def drawPanel( _ax, _memTime, _memEff ):
    Ls = np.arange( 1, 360.1, 0.2 )
    for _numRouters in [ 1, 3, 7
                         ]: ##range( 8 ):
        _attenuation1 = attenuation
        fname2 = ( 'entRateInd(R=%d)(att=%.3fdBkm,cohTime=%s%smemEff=%.2f,detEff=%.2f,swEff=%.2f,N=1E%d).txt' 
                     % (
                       _numRouters,
                        _attenuation1 * 1000,
                        '%.3fms' % ( _memTime[0] / 1e-3 ) if _memTime[0] > 0.0 else 'inf',
                        ( '+-%.2fmcs,' % ( _memTime[1] / 1e-6 )
                        if ( _memTime[0] > 0 and _memTime[1] > 0 )
                            else ',' ),
                        _memEff, det_eff, swap_probability, np.log10(_N) ) )
        data2 = np.loadtxt( srcDir + '/' + fname2 )
        reg2 = data2[ :, 1 ] > 0.0
        data2 = data2[ reg2, : ]

        ents = entRateInd( Ls*1000, _attenuation1, _memEff, det_eff, swap_probability, _numRouters )
        line, = _ax.semilogy( Ls, ents, lw = 2, ls = '--' )
        _ax.semilogy( data2[ :, 0 ]/1000, data2[ :, 1 ], lw = 3, color = line.get_color(), ms = msize, mec = 'none',
                    label = 'r = %d' % ( _numRouters ) )


plt.clf()
fig = plt.figure() #figsize=(3,4)
fsize = fig.get_size_inches()
#print(fsize)
fsize[1] *= 2.0

fig = plt.figure( figsize = fsize )
plt.subplots_adjust( top = 1-0.001, bottom = 0.06, left = 0.115, right = 1-0.025, hspace = 0.02 )
    #scaling = False

axes = []
for i in range( len( memTimes ) ):
    if len( axes ) == 0:
        axes.append( fig.add_subplot( len( memTimes ), 1, i + 1 ) )
    else:
        axes.append( fig.add_subplot( len( memTimes ), 1, i + 1, sharex = axes[i-1] ) )

    memTime = memTimes[i][0] if type( memTimes[i][0] ) is tuple else ( memTimes[i][0], 0.0 )
    drawPanel( axes[-1], memTime, memTimes[i][1] )
            
    axes[-1].set_ylim( ( 1e-1, 2e4 ) )
    axes[-1].tick_params( axis='y', direction='in', which='major', labelsize=13, right = True )
    axes[-1].tick_params( axis='y', direction='in', which='minor', labelsize=11, right = True )

    if i == 0:
        axes[-1].set_xlim( -2, 352 )

        axes[-1].xaxis.set_major_locator( MultipleLocator( 50 ) )
        axes[-1].xaxis.set_minor_locator( MultipleLocator( 10 ) )
                
        #plt.loglog( [2*2e5*_coherence_time_avg,]*2, [1, 2.5e4], 'k--', lw = 1.5 )
        axes[-1].legend( loc = 1, fontsize = 18, frameon = False, numpoints = 1 )

    axes[-1].tick_params( axis='x', direction='in', which='major', labelsize=13, top = True )
    axes[-1].tick_params( axis='x', direction='in', which='minor', labelsize=11, top = True )


    memTimeAvg = memTimes[i][0] if type( memTimes[i] ) is tuple else memTimes[i]
    annAvgLit = '%.0f' if memTimeAvg/1e-3 >= 10.0 else '%.1f'

    annAvgStr = annAvgLit % (memTimeAvg/1e-3)
    annStdStr = r'$\pm$%.2f' % (memTimes[i][1]/1e-3) if type( memTimes[i][0] ) is tuple else ''

    axes[-1].annotate( r'$\tau_\mathrm{mem}$ = %s ms'%(annAvgStr+annStdStr), xy=( 0.25, 0.76 ), xycoords='axes fraction',
                           fontsize=18,
                           #fontweight='bold',
                           horizontalalignment='left', verticalalignment='center' )
    axes[-1].annotate( r'$\mathcal{E}_\mathrm{mem}$ = %.0f %%'%(memTimes[i][1]*100), xy=( 0.25, 0.62 ), xycoords='axes fraction',
                           fontsize=18,
                           #fontweight='bold',
                           horizontalalignment='left', verticalalignment='center' )

    if showPanelIds:
        axes[-1].annotate( '%s' % panelIds[i], xy=( 0.03, 0.975 ), xycoords='axes fraction',
                           fontsize=22,
                           #fontweight='bold',
                           horizontalalignment='left', verticalalignment='top' )

    if i < len( memTimes ) - 1:
        plt.setp( axes[-1].get_xticklabels(), visible=False )
            
axes[-1].set_xlabel( 'Distance, km', fontsize = 18 )
fig.text( 0.025, 0.5, 'Entanglement gen. rate, 1/sec',
        size = 18, ha = 'center', va = 'center',
        #color = restColor,
        rotation = 90 )

    
if _saveFig:
    if not os.path.isdir(dstDir):
        print( 'creating output directory' )
        os.mkdir(dstDir)
    plt.savefig( dstDir + '/' + 'fig5-meff30-sweff50.pdf' )
plt.show()

    

