import os, time
import numpy as np

__seed = int( time.time() * 1000 ) % 2**32
np.random.seed( __seed )

doCalculations = False
plotGrapsOld = False
plotGraps = True
saveFig = True

srcDir = 'data'
dstDir = 'plots'
__overwrite = False

numRepetitions = 100000

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

def getAvgStDev( _a ):
    _numPts = _a.shape[0]
    _avg = np.sum( _a ) / _numPts
    _stdev = np.sqrt( np.sum( _a**2 ) / _numPts - _avg**2 )
    return _avg, _stdev

def getMinMax( _a ):
    _min, _max = _a[0], _a[0]
    for _e in _a:
        if _e < _min:
            _min = _e
        if _e > _max:
            _max = _e
    return _min, _max
                
def testSample( _p, _N ):
    dg = DistrGen( _p )
    _res = np.zeros( _N )
    for i in range( _N ):
        _res[i] = dg.test()

    _min, _max = getMinMax( _res ) 
    _avg, _stdev = getAvgStDev( _res )
        
    return _avg, _stdev, _min, _max

p = 0.001

if doCalculations:
    #N = 10
    if not os.path.isdir(dstDir):
        print( 'creating out/input directory' )
        os.mkdir(dstDir)
    
    Ns = list( range( 1, 21 ) ) #[1 ] + 

    tab = np.zeros( ( len( Ns ), 16 ) )

    fname = 'maxValStat(p=%.4f,N=1E%d).txt' % ( p, np.log10( numRepetitions ) )

    __toBeCalculated777 = True
    if not __overwrite:
        if os.path.isfile( srcDir + '/' + fname ):
            print( 'Already calculated:\n%s\nskipping' % ( srcDir + '/' + fname ) )
            __toBeCalculated777 = False
    else:
        if os.path.isfile( srcDir + '/' + fname ):
            print( 'Already calculated:\n%s\nwill be overwritten' % ( srcDir + '/' + fname ) )
            
    if __toBeCalculated777:
        for i in range( len( Ns ) ):
            avgs = np.zeros( numRepetitions )
            stdevs = np.zeros( numRepetitions )
            mins = np.zeros( numRepetitions )
            maxs = np.zeros( numRepetitions )
            
            for j in range( numRepetitions ):
                avgs[j], stdevs[j], mins[j], maxs[j] = testSample( p, Ns[i] )
                if j % 10000 == 0:
                    print( int( j / 10000 ), end = ' ' )
            print( '' )

            tab[ i, 0 ], tab[ i, 4 ] = getAvgStDev( avgs )
            tab[ i, 8 ], tab[ i, 12 ] = getMinMax( avgs )
            tab[ i, 1 ], tab[ i, 5 ] = getAvgStDev( stdevs )
            tab[ i, 9 ], tab[ i, 13 ] = getMinMax( stdevs )
            tab[ i, 2 ], tab[ i, 6 ] = getAvgStDev( mins )
            tab[ i, 10 ], tab[ i, 14 ] = getMinMax( mins )
            tab[ i, 3 ], tab[ i, 7 ] = getAvgStDev( maxs )
            tab[ i, 11 ], tab[ i, 15 ] = getMinMax( maxs )

            print( 'i=%d'%i, tab[i,3], '+-', tab[i,7] )

        tab *= p
        np.savetxt( dstDir + '/' + fname,
                    np.concatenate( ( np.array( Ns ).reshape( ( len(Ns), 1 ) ), tab ), axis = 1 ) )

if plotGrapsOld:
    import matplotlib.style
    #matplotlib.style.use('classic')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    if not os.path.isdir(srcDir):
        print( 'creating output directory' )
        os.mkdir(srcDir)

    plt.clf()
    ax = plt.gca()

    data = np.loadtxt( srcDir + '/maxValStat(p=%.4f,N=1E%d).txt' % ( p, np.log10( numRepetitions ) ) )
    xs = np.arange( 0, data[ -1, 0 ] + 0.005, 0.01 )
    plt.plot( xs, np.sqrt( xs ), color = 'k', lw = 2, label = r'$\sqrt{N}$' )
    plt.errorbar( data[ :, 0 ], data[ :, 4 ], yerr = data[ :, 8 ], marker = 'd',
                  color = 'red', ls = 'none', elinewidth = 0.75, capsize = 4,
                  capthick = 2.0 )

    plt.legend( loc = 2, fontsize = 16, frameon = False, numpoints = 1 )
    plt.xlim( -0.5, 21 )
    plt.ylim( -0.1, 5 )

    ax.tick_params( axis='both', direction = 'in', which='major', labelsize=13 )
    ax.tick_params( axis='both', direction = 'in', which='minor', labelsize=11 )

    ax.tick_params( axis='x', direction = 'in', which='major', labelsize=13, top = True )
    ax.tick_params( axis='x', direction = 'in', which='minor', labelsize=11, top = True )

    ax.tick_params( axis='y', direction = 'in', which='major', labelsize=13, right = True )
    ax.tick_params( axis='y', direction = 'in', which='minor', labelsize=11, right = True )

    ax.xaxis.set_major_locator( MultipleLocator( 5 ) )
    ax.xaxis.set_minor_locator( MultipleLocator( 1 ) )
    ax.yaxis.set_major_locator( MultipleLocator( 1 ) )
    ax.yaxis.set_minor_locator( MultipleLocator( 0.2 ) )
        
    plt.xlabel( r'Number of processes $N$', fontsize = 15 )
    plt.ylabel( r'$\mu(N)$', fontsize = 15 )
    
    if saveFig:
        plt.savefig( dstDir + '/fig4.eps' )
    plt.show()

if plotGraps:
    import matplotlib.style
    #matplotlib.style.use('classic')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator
    from plotLastFig import DistrGen

    if not os.path.isdir(srcDir):
        print( 'creating output directory' )
        os.mkdir(srcDir)

    plt.clf()
    fig = plt.figure()
    fsize = fig.get_size_inches()
    #print(fsize)
    fsize[1] *= 2
    fig = plt.figure( figsize = fsize )
    ax11 = fig.add_subplot( 2, 1, 1 )
    #ax21 = plt.gca()
    __seed = 20
    np.random.seed( __seed )

    NumLinks = 10
    P_elem = 1.0 / 4

    dgen = DistrGen( P_elem )
    triesDistr = np.zeros( NumLinks, dtype = np.int32 )

    for i in range( triesDistr.shape[0] ):
        triesDistr[i] = dgen.test()

    print( triesDistr )

    width = 0.4
    #plt.subplots_adjust( top = 1-0.03, bottom = 0.06, left = 0.05, right = 1-0.03, wspace = 0.06 )
    #ax11 = fig.add_subplot( 1, 1, 1 )
    x_pos = np.arange( triesDistr.shape[0] )
    #ax11.bar( x_pos, triesDistr )
    #ax11.set_ylim( 0, 5 )

    #ax12 = fig.add_subplot( 1, 2, 2 )

    #ax12.bar( x_pos, [ 1 ] * triesDistr.shape[0] )
    #ax12.set_ylim( 0, 5 )

    ax11.bar( x_pos, triesDistr, width = width, label = 'Individual' )
    ax11.bar( x_pos + width, [ 1 ] * triesDistr.shape[0], width = width, label = 'Synchronous' )
    ax11.plot( [ x_pos[0]-0.5*width, x_pos[-1]+1.5*width ], [1/P_elem]*2, color = 'k', lw = 2, ls = '--' )

    #ax11.set_ylim( 0, 14 )
    ax11.set_xlim( x_pos[0]-0.35, x_pos[-1]+0.75 )

    ax11.tick_params( axis='x', direction = 'in', which='major', labelsize=13, top = True )
    ax11.tick_params( axis='x', direction = 'in', which='minor', labelsize=11, top = True )

    ax11.tick_params( axis='y', direction = 'in', which='major', labelsize=13, right = True )
    ax11.tick_params( axis='y', direction = 'in', which='minor', labelsize=11, right = True )

    ax11.yaxis.set_major_locator( MultipleLocator( 2 ) )
    ax11.yaxis.set_minor_locator( MultipleLocator( 1 ) )

    #ax.xaxis.set_visible(False)
            
    #plt.xlabel( r'Number of processes $N$', fontsize = 15 )
    ax11.set_ylabel( r'Elem. link establishing time, $3L_1/v$', fontsize = 15 )
    ax11.set_xlabel( 'Elementary links', fontsize = 15 )

    plt.setp( ax11.get_xticklabels(), visible=False )
    ax11.legend( loc = 2, fontsize = 18, frameon = False )

    ax11.annotate( '(a)', xy=( 0.01, 0.975 ), xycoords='axes fraction',
                   fontsize=22,
                   #fontweight='bold',
                   horizontalalignment='left', verticalalignment='top' )

    ax21 = fig.add_subplot( 2, 1, 2 )

    data = np.loadtxt( srcDir + '/maxValStat(p=%.4f,N=1E%d).txt' % ( p, np.log10( numRepetitions ) ) )
    xs = np.arange( 0, data[ -1, 0 ] + 0.005, 0.01 )
    ax21.plot( xs, np.sqrt( xs ), color = 'k', lw = 2, label = r'$\sqrt{N}$' )
    ax21.errorbar( data[ :, 0 ], data[ :, 4 ], yerr = data[ :, 8 ], marker = 'd',
                  color = 'red', ls = 'none', elinewidth = 0.75, capsize = 4,
                  capthick = 2.0 )

    ax21.legend( loc = 2, fontsize = 16, frameon = False, numpoints = 1 )
    ax21.set_xlim( -0.5, 21 )
    ax21.set_ylim( -0.1, 5 )

    ax21.tick_params( axis='both', direction = 'in', which='major', labelsize=13 )
    ax21.tick_params( axis='both', direction = 'in', which='minor', labelsize=11 )

    ax21.tick_params( axis='x', direction = 'in', which='major', labelsize=13, top = True )
    ax21.tick_params( axis='x', direction = 'in', which='minor', labelsize=11, top = True )

    ax21.tick_params( axis='y', direction = 'in', which='major', labelsize=13, right = True )
    ax21.tick_params( axis='y', direction = 'in', which='minor', labelsize=11, right = True )

    ax21.xaxis.set_major_locator( MultipleLocator( 5 ) )
    ax21.xaxis.set_minor_locator( MultipleLocator( 1 ) )
    ax21.yaxis.set_major_locator( MultipleLocator( 1 ) )
    ax21.yaxis.set_minor_locator( MultipleLocator( 0.2 ) )
        
    ax21.set_xlabel( r'Number of processes $N$', fontsize = 15 )
    ax21.set_ylabel( r'$\mu(N)$', fontsize = 15 )

    ax21.annotate( '(b)', xy=( 0.01, 0.975 ), xycoords='axes fraction',
                   fontsize=22,
                   #fontweight='bold',
                   horizontalalignment='left', verticalalignment='top' )
    
    if saveFig:
        plt.savefig( dstDir + '/fig4.svg' )
    plt.show()

