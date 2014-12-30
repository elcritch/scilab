#!/opt/local/bin/python3.3

import shutil, re, sys, os, itertools, argparse, json

from pylab import *
from scipy.stats import exponweib, weibull_max, weibull_min
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

from scilab.tools.project import *
from scilab.tools.graphing import DataMax

# from WaveMatrixToolsPy3 import *
from scilab.tools.instroncsv import csvread

import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing 
import scilab.tools.scriptrunner as ScriptRunner
import scilab.tools.json as Json

import collections

# sys.path.append("../../03_DataReduction/libraries/")
import scilab.tools.dynamicmodulus as DynamicModulus
# from scilab.tools.dynamicmodulus import find_index
# from DataToolsPy3 import find_index

PlotData = namedtuple('PlotData', 'array label units max')


def find_index(t, times):
    for i, tau in enumerate(times):
        if t < tau:
            return i


## Main
def data_find_max(name, data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=name)

handler(file=file,file_object=file_obect, args=args)
    
    data = csvread(file_path)
    data_json = Json.load_data(file_parent, file_name)

    if not data_json:
        logging.warn("relax_stage: Cannot process file: "+file_path)
        return
        
    # json data
    details = DataTree()
    details.gaugeLength = data_json['gauge']['length']        
    details.area = data_json['measurements']['area']['value']

    # graph
    data, details = data_cleanup_relaxation(data, details, file_parent, data_json, args)    
    graph_relaxation(file_name, file_parent, data, details, args)

    return

def data_cleanup_relaxation(data, details, file_parent, data_json, args):
    
    data.maxes = {}
    data.maxes['displacement'] = data_find_max('displacement', data.displacement.array)
    if 'load' not in data.keys():
        data.load = data.loadLinearLoad1 # choose Instron
        
    stress = data.load()/details.area
    strain = data.displacement()/details.gaugeLength

    data.maxes['stress'] = data_find_max('stress', stress)
    data.maxes['strain'] = data_find_max('strain', strain)
    
    data.stress = PlotData(array=stress, label="Stress", units="MPa", max=None)
    data.strain = PlotData(array=strain, label="Stress", units="∆", max=None)
    
    npslice = data._getslices('step')[args.step]
    t = data.totalTime.array[npslice]
    disp = data.displacement()[npslice]
    force = data.load()[npslice]
    stress = data.stress.array[npslice]
    strain = data.strain.array[npslice]
    
    # t = data.totalTime.array
    # disp = data.displacement.array
    # force = data.load.array
    
    # debug(disp)
    
    # find the time delta, to cut off the first few cycles
    t_delta = (t[-1] - t[0])*0.01

    debug(t[0], t[-1], t_delta, t[0]+t_delta*args.begin, t[-1]-t_delta*args.end)
    a, b = find_index(t[0]+t_delta*args.begin, t), find_index(t[-1]-t_delta*args.end, t)
    
    t_trim = t[a:b]
    strain_trim = strain[a:b]
    stress_trim = stress[a:b]
    
    debug(t, t_delta, a, b, args.begin, args.end)
    
    strain_fit = DynamicModulus.SineFitData.fit_leastsq( t_trim, strain_trim)
    stress_fit = DynamicModulus.SineFitData.fit_leastsq( t_trim, stress_trim)
    # stress_fit2 = DynamicModulus.SineFitData.fit_leastsq( t_trim, stress_trim)

    debug(strain_fit.data, stress_fit.data)
    
    # dyn_modulus = DynamicModulus.fit_data_calculate_dynamic_modulus(t, stress=stress, strain=strain)
    dyn_modulus = DynamicModulus.calculate_dynamic_modulus(stress_fit, strain_fit)

    debug(dyn_modulus)

    # save dyn mod
    data_json['dyn_modulus'] = { 'amp':dyn_modulus[0], 'phase':dyn_modulus[1]}
    Json.write_json(file_parent, data_json, dbg=True)
    
    graph = DataTree()
    
    graph.t = t
    graph.t_trim = t_trim
    graph.disp = disp
    graph.force = force
    graph.stress = stress
    graph.strain = strain
    graph.dyn_modulus = dyn_modulus
    graph.strain_fit = strain_fit
    graph.stress_fit = stress_fit
    # graph.stress_fit2 = stress_fit2
    
    return (graph, details)

def graph_relaxation(file_name, file_parent, data, details, args):
    
    fig, (ax1,ax2) = plt.subplots(ncols=2, figsize=(14,6))
    # ax2 = ax1.twinx() # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>

    ax1.plot(data.t, data.strain, label="Stress|DynaCell [MPa]")
    ax2.plot(data.t, data.stress, label="Strain|Stretch Ratio [λ]", )

    ax1.set_ylabel('$Stretch Ratio [\lambda]$')
    ax2.set_ylabel('$Force [N]$')

    ax1.plot(data.t_trim, data.strain_fit( data.t_trim), '.', label='Strain fit')
    ax2.plot(data.t_trim, data.stress_fit( data.t_trim), '.', label='Stress fit')
    ax2.plot(data.t_trim, data.stress_fit( data.t_trim)+data.stress_fit.data[3]/2, '.', label='Stress fit (shift)')

    ax1.legend(loc=3,fontsize=8, )
    ax2.legend(loc=4,fontsize=8, )
    
    ax1.set_title("Dynamic Strain Fit (%.1f%% of %.2f mm)"%(200*data.dyn_modulus[0]/details.gaugeLength, details.gaugeLength))
    ax2.set_title("Dynamic Stress Fit")

    # print("dbg.stress:", dbg.stress.data)
    
    dyn_modulus = data.dyn_modulus

    message1 = "Dynamic Modulus:%5.2f, Phase:%5.2f"%data.dyn_modulus
    # message += "\n Orig Dynamic Modulus: (%5.2f %5.2f)"%((stress_amp/strain_amp), (stress_phase-strain_phase))
    # message2 = "Linear Decay Amt:%5.2f| Rate:%5.2f"%(data.stress_fit.data.decayAmt  , data.stress_fit.data.decayRate )
    # message3 = "Multpl Decay Amt:%5.2f| Rate:%5.2f"%(data.stress_fit2.data.decayAmt  , data.stress_fit2.data.decayRate )

    # fig.tight_layout()
    fig.subplots_adjust(hspace=1.1, )

    print(message1)
    # print(message2)
    # print(message3)

    handles, labels = ax1.get_legend_handles_labels()
    lgd = ax1.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.2,-0.07))

    fig.text(.45, -.04, '\n'.join([message1])) #, message2, message3]))

    handles, labels = ax2.get_legend_handles_labels()
    lgd2 = ax2.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.8,-0.07))

    base_file_name = "%s (%s)"%(file_name[:file_name.index('.steps')], "dynamic_modulus")    
    fig.text(.45, .95, file_name)
    
    if args.only_first:
        plt.show(block=True,  )
    
    Graphing.fig_save(fig, os.path.join(file_parent, 'img'), name=base_file_name, type='.png', lgd=lgd, lgd2=lgd2)
    # Graphing.fig_save(fig, os.path.join(file_parent, 'img', 'eps'), name=base_file_name, type='.eps', lgd=lgd, lgd2=lgd2)
    
    plt.close()
    
    return
    

def main():
    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)
    parser.add_argument("-s", "--step", default=0, type=int)
    parser.add_argument("-b", "--begin", default=75, type=float)
    parser.add_argument("-e", "--end", default=10, type=float)

    test_args = []
    
    ## Test

    # project = "Test4 - transverse fatigue (scilab.mf.pre)/trans-fatigue-trial1/"
    # test_args += ['--step', '0'] # only first

    project = "Test4 - transverse fatigue (scilab.mf.pre)/test4(trans-uts)/"
    test_args += ['--step', '1'] # only first
    
    test_args += ['--begin', '80.30'] # only first
    test_args += ['--end', '4.8'] # only first
    
    # fileglob = "{R}/{P}/*/*.tracking.csv".format(R="/Users/elcritch/GDrive/Research/",P=project)
    fileglob = "{R}/{P}/*/*.tracking.csv".format(R=RAWDATA,P=project)
    # fileglob = "{R}/{P}/*/09sep16.1-x3-4.steps.tracking.csv".format(R=RAWDATA,P=project)
    
    test_args += ["--glob", fileglob] 
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args)
    
    # Parse command line if not running test args.
    if 'args' not in locals():
        args = parser.parse_args()
    
    ScriptRunner.process_files_with(args=args, handler=handler)
    
    
if __name__ == '__main__':
    main()


