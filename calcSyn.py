import sys
import MultiSwappingSyn as syn

def getParametersList( _numCoresToUse ):
    N = 10000000
    coherence_time_avg = 0.1e-3
    coherence_time_stdev = 0.2 * coherence_time_avg
    attenuation = 0.0002
    mem_eff = 0.9 #9 #3
    det_eff = 0.8 #3
    swap_probability = 0.5 #5 #9
    swap_degradation = 0.95
    maxNumRepeaters = 2
    max_distance_km = 13
    distance_step_km = 1.0/3
    light_speed = 2e-4
    numCoresToUsee = _numCoresToUse
    
    pars0 = syn.InputParameters( max_distance_km, distance_step_km, light_speed, attenuation, coherence_time_avg, coherence_time_stdev,
                           mem_eff, det_eff, swap_probability, swap_degradation, N, 0, numCoresToUsee )

    pl = [ pars0 ]
    """
    pl.append( syn.InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = 0.2e-3
    pl[-1].max_distance_km = 50
    pl[-1].distance_step_km = 1.0

    pl.append( syn.InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = 0.4e-3
    pl[-1].max_distance_km = 90
    pl[-1].distance_step_km = 1.0
    """
    pl.append( syn.InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = 0.5e-3
    pl[-1].max_distance_km = 48
    pl[-1].distance_step_km = 0.5
    """
    pl.append( syn.InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = 0.6e-3
    pl[-1].max_distance_km = 125
    pl[-1].distance_step_km = 1.0

    pl.append( syn.InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = 0.8e-3
    pl[-1].distance_step_km = 2.0
    pl[-1].max_distance_km = 152
    """
    pl.append( syn.InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = 1.0e-3
    pl[-1].distance_step_km = 1.0
    pl[-1].max_distance_km = 85
    """
    pl.append( syn.InputParameters().copy_from( pl[-1] ) )
    pl[-1].coherence_time_avg = -1
    pl[-1].distance_step_km = 2.0
    pl[-1].coherence_time_stdev = 0
    pl[-1].max_distance_km = 152
    """
    return pl

def main():
    tpn = int( sys.argv[2] ) if len( sys.argv ) > 2 else 32

    numCoresToUse = 32
    numRepsToCalculate = [ 1, 2, 3,
                           4
                           ]
    paramsToCalculate = getParametersList( tpn )
    
    if len( sys.argv ) > 1:
        key = sys.argv[1]
        isJobNo = False
        if key[0] != '-':
            try:
                jobNo = int( key )
                isJobNo = True
            except ValueError as e:
                print( str( e ) )
                print( 'a key or job no was expected' )
                return

            if isJobNo:
                pass
            else:
                if key[1] != 'n':
                    print( '-n key was expexted' )
                    return
    else:
        print( 'usage:\n python calcSyn <-n or jobNo> [numCoresToUse]' )

    if not isJobNo:
        print( len( numRepsToCalculate ) * len( paramsToCalculate ) )
    else:
        paramIdx = jobNo // len( numRepsToCalculate )
        numRepsIdx = jobNo % len( numRepsToCalculate )
        _numRepeaters = numRepsToCalculate[ numRepsIdx ]
        ps = paramsToCalculate[ paramIdx ]
        print( 'numRepeaters = %d, coherenceTimeAvg = %.1f ms' % ( _numRepeaters,
                                                                   ps.coherence_time_avg / 1e-3 ) )

        syn.calculate( _numRepeaters, ps.max_distance_km, ps.distance_step_km, ps.light_speed, ps.attenuation,
                               ( ps.coherence_time_avg, ps.coherence_time_stdev ),
                               ps.mem_eff, ps.det_eff, ps.swap_probability, ps.swap_degradation, ps.N, 
                               num_cores_to_use = ps.num_cores_to_use )

if __name__ == '__main__':
    main()
