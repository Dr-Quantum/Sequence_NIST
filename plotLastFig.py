import os, time
import numpy as np

import matplotlib.style
import matplotlib as mpl
#mpl.style.use('classic')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

plotFig = True
saveFig = True

class DistrGen():
    def __init__( self, _p ):
        self.p = _p
        assert _p > 0.0 and _p <= 1.0

    def test( self ):
        _i = 0
        while True:
            _i += 1
            if np.random.random_sample() <= self.p:
                break
        return _i



if plotFig:

    #__seed = int( time.time() * 1000 ) % 2**32
    __seed = 20
    np.random.seed( __seed )

    NumLinks = 10
    P_elem = 1.0 / 4

    dgen = DistrGen( P_elem )
    triesDistr = np.zeros( NumLinks, dtype = np.int32 )

    for i in range( triesDistr.shape[0] ):
        triesDistr[i] = dgen.test()

    print( triesDistr )

    plt.clf()
    ax = plt.gca()
    #fig = plt.figure()
    width = 0.4
    #plt.subplots_adjust( top = 1-0.03, bottom = 0.06, left = 0.05, right = 1-0.03, wspace = 0.06 )
    #ax11 = fig.add_subplot( 1, 1, 1 )
    x_pos = np.arange( triesDistr.shape[0] )
    #ax11.bar( x_pos, triesDistr )
    #ax11.set_ylim( 0, 5 )

    #ax12 = fig.add_subplot( 1, 2, 2 )

    #ax12.bar( x_pos, [ 1 ] * triesDistr.shape[0] )
    #ax12.set_ylim( 0, 5 )

    ax.bar( x_pos, triesDistr, width = width, label = 'Individual' )
    ax.bar( x_pos + width, [ 1 ] * triesDistr.shape[0], width = width, label = 'Synchronous' )
    ax.plot( [ x_pos[0]-0.5*width, x_pos[-1]+1.5*width ], [1/P_elem]*2, color = 'k', lw = 2, ls = '--' )

    ax.set_ylim( 0, 14 )
    ax.set_xlim( x_pos[0]-0.35, x_pos[-1]+0.75 )

    ax.yaxis.set_major_locator( MultipleLocator( 2 ) )
    ax.yaxis.set_minor_locator( MultipleLocator( 1 ) )

    #ax.xaxis.set_visible(False)
            
    #plt.xlabel( r'Number of processes $N$', fontsize = 15 )
    ax.set_ylabel( r'Elementary link establishing time, $3L_1/v$', fontsize = 15 )
    ax.set_xlabel( 'Elementary links', fontsize = 15 )

    plt.setp( ax.get_xticklabels(), visible=False )
    plt.legend( loc = 2, fontsize = 18, frameon = False )

    if saveFig:
        plt.savefig( 'plots/fig31.pdf' )

    plt.show()
