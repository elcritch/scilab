#!/opt/local/bin/python3.3
# coding: utf-8

# In[1]:

# must load before loading notebooks
# import NotebookLoaderPy3
# from DataToolsPy3 import *
# from WaveMatrixToolsPy3 import *
# import DefaultGraphsPy3


# In[2]:

import numpy as np
import scipy.signal
from numpy import pi as pi
from scipy.optimize import leastsq
import pylab as plt
import collections
from functools import reduce

if __name__ != '__main__':
    from ntm.Tools.Project import *
else:
    from Project import *

# ## Example Simple Fit
# 
# Example scipy code. It fits a sine using an initial estimate followed by using a least squares optimization. 
# 
# 

# In[3]:

if __name__ == "__main__":
    
    # Example from:
    # [how-do-i-fit-a-sine-curve-to-my-data-with-pylab-and-numpy](http://stackoverflow.com/questions/16716302/how-do-i-fit-a-sine-curve-to-my-data-with-pylab-and-numpy)

    N = 1000 # number of data points
    t = np.linspace(0, 6*np.pi, N)
    data = 3.0*np.sin(2*(t+0.75)) + np.random.randn(N)/2.0 # create artificial data with noise

    guess_mean = np.mean(data)
    guess_std = 3*np.std(data)/(2**0.5)
    guess_phase = 0

    peakfind = scipy.signal.find_peaks_cwt(data, 1000.0/(8*np.pi)*np.arange(1, 2, 1))
    print("peakfind:", peakfind)
    
    t1 = np.array([ t[p] for p in peakfind ])
    d1 = [ data[p] for p in peakfind ]
    
    guess_freq = np.array(t1[1:]-t1[:-1]).mean()/(np.pi/2)
    guess_phase = t1[0]*(np.pi)
    print("reducde:std:", np.array(t1[1:]-t1[:-1]).mean())
    
    # we'll use this to plot our first estimate. This might already be good enough for you
    data_first_guess = guess_std*np.sin(guess_freq*(t+guess_phase)) + guess_mean

    # Define the function to optimize, in this case, we want to minimize the difference
    # between the actual data and our "guessed" parameters
    optimize_func = lambda x: x[0]*np.sin(x[3]*(t+x[1])) + x[2] - data

    fit = leastsq(optimize_func, [guess_std, guess_phase, guess_mean, guess_freq])[0]

    print("leastsq fit:", fit)
    
    est_std, est_phase, est_mean, est_freq = fit
    # recreate the fitted curve using the optimized parameters
    data_fit = est_std*np.sin(est_freq*(t+est_phase)) + est_mean

    fig, (ax1) = plt.subplots(nrows=1, figsize=(10,6))
    ax1.plot(t, data, '.')
    ax1.plot(t, data_fit, label='after fitting')
    ax1.plot(t, data_first_guess, label='first guess')
    ax1.scatter(t1, d1, color='red')
    ax1.set_xlim(0,20)
    ax1.legend()


# ## Fit Function
# 
# Simple API to help hold fit data and make it simpler to re-use. 
# 
# 

# In[4]:

def smooth_data(data, window='flat', window_len = 9):
    """ Apply smoothing to the data using either a flat window, or other window. 
    
    See http://wiki.scipy.org/Cookbook/SignalSmooth
    """
    
    s=np.r_[data[window_len-1:0:-1],data,data[-1:-window_len:-1]]

    if window == 'flat': #moving average
        w=np.ones(window_len,'d')
    else:
        w=getattr(np, window)(window_len)

    ret = np.convolve(w/w.sum(),s,mode='valid')
    
    return ret[:len(data)] 

if __name__ == "__main__":
    N = 1000 # number of data points
    t = np.linspace(0, 4*np.pi, N)
    data = 3.0*np.sin(1.5*(t+0.2)) + 0.5 + np.random.randn(N) # create artificial data with noise

    data1 = smooth_data(data, window='flat', window_len=40)
    data2 = smooth_data(data, window='bartlett', window_len=40)
    data3 = smooth_data(data, window='hanning', window_len=40)
    
    plt.plot(t, data, '.')
    plt.plot(t, data1, label='flat')
    plt.plot(t, data2, label='bartlett')
    plt.plot(t, data3, label='hanning')
    plt.legend()

    plt.show(block=True)

# In[5]:

def fit_estimate_period_peaks(t, y_data, width_min=10, width_max=20, dbg=None):
    # smooth the data 
#     y_data = smooth_data(y_data, window_len=20)
    
    peak_widths = np.array( list(reversed([1.0*len(y_data)/n for n in range(width_min,width_max)]))) 
    
    peakfind = scipy.signal.find_peaks_cwt(y_data, peak_widths )
    t_maxs = np.array([ t[p] for p in peakfind ])
    d_maxs = np.array([ y_data[p] for p in peakfind ])

    peakfind = scipy.signal.find_peaks_cwt(y_data.mean()-y_data, peak_widths )
    t_mins = np.array([ t[p] for p in peakfind ])
    d_mins = np.array([ y_data[p] for p in peakfind ])
    
    if dbg: dbg.y_data = y_data
        
    return ( (t_maxs, d_maxs), (t_mins, d_mins) )

def fit_estimate_period_peaks2(t, y_data, width_min=10, width_max=20, dbg=None):
    # smooth the data 
    y_data = smooth_data(y_data, window_len=20)
    
    
    peak_widths = np.array( list(reversed([1.0*len(y_data)/n for n in range(width_min,width_max)]))) 
    
    peakfind = scipy.signal.argrelmax(y_data, order=50)[0]
    t_maxs = np.array([ t[p] for p in peakfind ])
    d_maxs = np.array([ y_data[p] for p in peakfind ])

    peakfind = scipy.signal.argrelmin(y_data, order=50)[0]       
    t_mins = np.array([ t[p] for p in peakfind ])
    d_mins = np.array([ y_data[p] for p in peakfind ])
    
    if dbg:
        dbg.y_data = y_data
        
    return ( (t_maxs, d_maxs), (t_mins, d_mins))

        


# In[6]:

def fit_sinusoidal_freq_est(t, y_data, dbg=None, peaks_func=fit_estimate_period_peaks2):
    """ Estimate the parameters of the input wave.  """
    (t_maxs, d_maxs), (t_mins, d_mins) = peaks_func(t, y_data)
    
    guess_period_max = np.array(t_maxs[1:]-t_maxs[:-1]).mean()
    guess_period_min = np.array(t_mins[1:]-t_mins[:-1]).mean()
    
    guess_period = (guess_period_max+guess_period_min)/2.0    
    guess_freq = 1.0/(guess_period)
    
#     guess_phase = pi*guess_freq*t[data_zeros[0]] 
    guess_phase = 0.0
    
    if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k not in 't y_data' ]
    
    return (guess_freq, guess_phase)

# Test: fit_sinusoidal_freq_est
if __name__ == "__main__":
    
    M = 5
    N = 500 # number of data points
    t = np.linspace(0, 4*pi, N)
    
    fig, (axes) = plt.subplots(nrows=M, figsize=(12,16))

    for i, ax in enumerate(axes):
        freq = 0.16
        phase = 2*pi/M*i
        
        data = 3.0*np.sin(2*pi*freq*t + phase) + 0.5 + np.random.randn(N) # create artificial data with noise

        dbg = DebugData()
        guess_freq, guess_phase = fit_sinusoidal_freq_est(t, data, dbg=dbg, peaks_func=fit_estimate_period_peaks)
        smooth = smooth_data(data, window_len=20)

#         est_data = SineFitData(amp=4, freq=guess_freq, phase=guess_phase, mean=0.0)
        
        print("")
        msg_orig = "Orig F: %5.2f P: %5.2f"%(freq, phase) 
        msg = "Est. F: %5.2f P: %5.2f"%(guess_freq, guess_phase) 
        print ("i:", i, msg_orig)
        
#         print("dbg:", dbg.keys())
        
        ax.plot(t, data, '.', label=msg_orig)
#         ax.plot(t, smooth, label=msg)
#         ax.plot(t, est_data(t), label="est "+msg)
        ax.scatter(dbg.t_maxs, dbg.d_maxs, color="red", linewidth=4.0)
        ax.scatter(dbg.t_mins, dbg.d_mins, color="orange", linewidth=4.0)

        guess_freq, guess_phase = fit_sinusoidal_freq_est(t, data, dbg=dbg, peaks_func=fit_estimate_period_peaks2)
        ax.scatter(dbg.t_maxs, dbg.d_maxs, color="aqua", linewidth=4.0)
        ax.scatter(dbg.t_mins, dbg.d_mins, color="purple", linewidth=4.0)
        ax.legend(fontsize=12)

    plt.show(block=True)

# In[7]:

# class TestData(collections.namedtuple('TestData', 'mean std phase freq')):
#     def __init__(self, *args, **kwargs):
#         self = super().__new__(self, *args)
        
#         self.func = lambda fit, x: fit[0] * np.sin(2*np.pi*fit[3]*x + fit[1]) + fit[2]

# class TestDataFit:
#     def __init__(self, names):
#         self.names = names.split()
#         self.__params = collections.namedtuple('Params'+self.__class__.__name__, self.names)

# class TestData1(TestDataFit):
#     def __init__(self, *args, **kwargs):
#         super().__init__('mean std phase freq')
        
#         self.func = lambda fit, x: fit[0] * np.sin(2*np.pi*fit[3]*x + fit[1]) + fit[2]

# t1 = TestData1()
# print("T1:", t1, [ n for n in dir(t1) if '__' not in n ])
# print("T1:", t1.params.mean


# In[8]:

class FitData(object):
    
    @classmethod 
    def fit_leastsq(cls, t, data, user_estimate=None, dbg=None):
        """ Perform a fitting using a least squares optimiaztion. """
        guess = cls.estimate(t, data) if not user_estimate else user_estimate
        if dbg: dbg.estimate = guess
        optimized_params, other = leastsq(guess.as_optimize_func(t, data), guess.as_tuple())

        if dbg: dbg.optimized_params = optimized_params
        if dbg: dbg.optimized_other = other
            
        fit_lstsq = cls(*optimized_params.tolist())
        return fit_lstsq

# def __new__(cls, left, right):
#         self = super(Edge, cls).__new__(cls, left, right)


# In[18]:

class SineFitData(FitData):
    
    def __init__(self, amp=0.0, freq=0.0, phase=0.0, mean=0.0, ):
        self.Data = namedtuple('Data','amp, freq, phase, mean'.split(', '), rename=True)
        self.data = self.Data(amp, freq, phase, mean)
        self.func = lambda fit, x: fit[0]*np.sin( 2*np.pi*fit[1]*x + fit[2] ) + fit[3]
        
    def __call__(self, t):
        return self.func(self.as_tuple(), t)

    def as_optimize_func(self, x, y_data):
        optimize_func = lambda fit: self.func(fit, x) - y_data
        return optimize_func
    
    def as_tuple(self):
        return self.data
    
    @classmethod 
    def fit_leastsq(cls, t, data, user_estimate=None, dbg=None):
        fit = super().fit_leastsq(t, data, user_estimate, dbg)
        f = fit.data
        if f[0] < 0.0:
            return cls(*( [abs(f[0]), f[1], f[2]+np.pi, f[3], ]))
        else:
            return fit
        
    @classmethod
    def estimate(cls, t, data, dbg=DebugNone()):
        guess_mean = np.mean(data)
        guess_std = 3*np.std(data)/(2**0.5)
        
        if dbg: dbg.freq_est = DebugData()
            
        # guess_freq, guess_phase = fit_sinusoidal_freq_est(t, data, dbg=dbg.freq_est)
        guess_freq, guess_phase = fit_sinusoidal_freq_est(t, data)
        guess_phase = guess_phase * 2.0*np.pi

        if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k.startswith('guess') ]
        
        return cls(mean=guess_mean, amp=guess_std, phase=guess_phase, freq=guess_freq)
    
    
## Tests: fit_sinusoidal_lstsq
if __name__ == "__main__":
    print("\nTest2 \n"+"="*15)
    N = 500 # number of data points
    t = np.linspace(0, 4*np.pi, N)
    data = 3.0*np.sin(2*np.pi*0.25*t) + 0.5 + np.random.randn(N) # create artificial data with noise

    dbg = DebugData()
    dbgLSQ = DebugData()
    
    guess = SineFitData.estimate(t, data, dbg=dbg)
    lstsq = SineFitData.fit_leastsq(t, data, dbg=dbgLSQ)
    
    print("guess:", guess.as_tuple())
    print("dbgLSQ:", dbgLSQ.estimate.as_tuple())
    print("dbgLSQ:optimized_params", dbgLSQ.optimized_params)
    print("dbgLSQ:optimized_other", dbgLSQ.optimized_other)
    
    plt.plot(t, data, '.')
    plt.plot(t, guess(t), label='guess')
    plt.plot(t, lstsq(t), label='lstsq')
    
#     px, py = fit_estimate_period_peaks(t, data, width_min=1, width_max=7)
    # px, py = dbg.freq_est.t_maxs, dbg.freq_est.d_maxs
    # plt.scatter(px, py, color="red", linewidth=3.0)
    # px, py = dbg.freq_est.t_mins, dbg.freq_est.d_mins
    # plt.scatter(px, py, color="orange", linewidth=3.0)
    plt.legend()
    plt.show()
    
    plt.show(block=True)
    

## Test Phase Calculation

# if __name__ == "__main__":
#     print("\nTest3 \n"+"="*15)

#     N = 500 # number of data points
#     t = np.linspace(0, 4*np.pi, N)
#     data = 3.0*np.sin(t+2) + 0.5 + np.random.randn(N) # create artificial data with noise

#     debug = datatree()
#     guess = SineFitData.estimate(t, data, debug)
#     print("estimate:dbg:", debug)
#     lstsq = SineFitData.fit_leastsq(t, data)
    
#     plt.plot(t, data, '.')
#     plt.plot(t, guess(t), label='guess')
#     plt.plot(t, lstsq(t), label='lstsq')
#     plt.legend()
#     plt.show()
    


# In[26]:

class SineFitWithViscoElastic(FitData):
    
    def __init__(self, decayAmt=0.0, decayRate=0.0, amp=0.0, freq=0.0, phase=0.0, mean=0.0, ):
        self.Data = namedtuple('Data','decayAmt, decayRate, amp, freq, phase, mean'.split(', '), rename=True)
        self.data = self.Data(decayAmt, decayRate, amp, freq, phase, mean)
        self.func = lambda fit, x: (fit[0]*np.exp(-fit[1]*x))+fit[2]*np.sin( 2*np.pi*fit[3]*x + fit[4] ) + fit[5]
        
    def __call__(self, t):
        return self.func(self.as_tuple(), t)

    def as_optimize_func(self, x, y_data):
        optimize_func = lambda fit: self.func(fit, x) - y_data
        return optimize_func
    
    def as_tuple(self):
        return self.data
    
    @classmethod
    def estimate(cls, t, data, dbg=DebugNone()):

        guess_sine = SineFitData.fit_leastsq(t, data).data
        
        guess_initamp = guess_sine.amp/6.0
        guess_halflife = 1/guess_sine.freq

        if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k.startswith('guess') ]        
        
        return cls(mean=guess_sine.mean, amp=guess_sine.amp, phase=guess_sine.phase, freq=guess_sine.freq,
                   decayAmt=guess_initamp, decayRate=guess_halflife)
    



## Tests: fit_sinusoidal_lstsq
if __name__ == "__main__":
    print("\nTest2 \n"+"="*15)
    N = 1000 # number of data points
    t = np.linspace(0, 8*np.pi, N)
    
    amp_decay = 1+2.5*np.exp(-t/1.75)
    # create artificial data with noise
    data = amp_decay+3.0*np.sin(t) + 0.5 + np.random.randn(N) # create artificial data with noise

    dbg = DebugData()
    dbgLSQ = DebugData()
    
    guess = SineFitWithViscoElastic.estimate(t, data, dbg=dbg)
    lstsq = SineFitWithViscoElastic.fit_leastsq(t, data, dbg=dbgLSQ)
    
    print("guess:", guess.as_tuple())
    print("dbgLSQ:", dbgLSQ.estimate.as_tuple())
    print("dbgLSQ:optimized_params", dbgLSQ.optimized_params)
    print("dbgLSQ:optimized_other", dbgLSQ.optimized_other)
    
    plt.plot(t, data, '.')
    plt.plot(t, guess(t), label='guess')
    plt.plot(t, lstsq(t), label='lstsq')
    
#     px, py = fit_estimate_period_peaks(t, data, width_min=1, width_max=7)
#     px, py = dbg.freq_est.t_maxs, dbg.freq_est.d_maxs
#     plt.scatter(px, py, color="red", linewidth=3.0)
#     px, py = dbg.freq_est.t_mins, dbg.freq_est.d_mins
#     plt.scatter(px, py, color="orange", linewidth=3.0)
    plt.legend()
    
    plt.show(block=True)
    


# In[19]:

class SineAndExpFitData(FitData):
    
    def __init__(self, decayAmt=0.0, decayRate=0.0, amp=0.0, freq=0.0, phase=0.0, mean=0.0, ):
        self.Data = namedtuple('Data','decayAmt, decayRate, amp, freq, phase, mean'.split(', '), rename=True)
        self.data = self.Data(decayAmt, decayRate, amp, freq, phase, mean)
        self.func = lambda fit, x: (fit[0]*np.exp(-fit[1]*x)+fit[2])*np.sin( 2*np.pi*fit[3]*x + fit[4] ) + fit[5]
        
    def __call__(self, t):
        return self.func(self.as_tuple(), t)

    def as_optimize_func(self, x, y_data):
        optimize_func = lambda fit: self.func(fit, x) - y_data
        return optimize_func
    
    def as_tuple(self):
        return self.data
    
    @classmethod
    def estimate(cls, t, data, dbg=DebugNone()):

        guess_sine = SineFitData.fit_leastsq(t, data).data
        
        guess_initamp = guess_sine.amp/6.0
        guess_halflife = 1/guess_sine.freq

        if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k.startswith('guess') ]        
        
        return cls(mean=guess_sine.mean, amp=guess_sine.amp, phase=guess_sine.phase, freq=guess_sine.freq,
                   decayAmt=guess_initamp, decayRate=guess_halflife)
    



## Tests: fit_sinusoidal_lstsq
if __name__ == "__main__":
    print("\nTest2 \n"+"="*15)
    N = 1000 # number of data points
    t = np.linspace(0, 8*np.pi, N)
    
    amp_decay = 1+2.5*np.exp(-t/1.75)
    # create artificial data with noise
    data = 3.0*amp_decay*np.sin(t) + 0.5 + np.random.randn(N) # create artificial data with noise

    dbg = DebugData()
    dbgLSQ = DebugData()
    
    guess = SineAndExpFitData.estimate(t, data, dbg=dbg)
    lstsq = SineAndExpFitData.fit_leastsq(t, data, dbg=dbgLSQ)
    
    print("guess:", guess.as_tuple())
    print("dbgLSQ:", dbgLSQ.estimate.as_tuple())
    print("dbgLSQ:optimized_params", dbgLSQ.optimized_params)
    print("dbgLSQ:optimized_other", dbgLSQ.optimized_other)
    
    plt.plot(t, data, '.')
    plt.plot(t, guess(t), label='guess')
    plt.plot(t, lstsq(t), label='lstsq')
    
#     px, py = fit_estimate_period_peaks(t, data, width_min=1, width_max=7)
#     px, py = dbg.freq_est.t_maxs, dbg.freq_est.d_maxs
#     plt.scatter(px, py, color="red", linewidth=3.0)
#     px, py = dbg.freq_est.t_mins, dbg.freq_est.d_mins
#     plt.scatter(px, py, color="orange", linewidth=3.0)
    plt.legend()
    
    plt.show(block=True)
    


# In[13]:

def calculate_dynamic_modulus(stress, strain):
    dyn_modulus = stress.data.amp/strain.data.amp
    dyn_phase =  strain.data.phase - stress.data.phase
    return (dyn_modulus, dyn_phase)

def fit_data_calculate_dynamic_modulus(t, *, stress, strain, dbg=DebugNone()):

    strain_fit = SineFitWithViscoElastic.fit_leastsq(t, strain)
    stress_fit = SineFitWithViscoElastic.fit_leastsq(t, stress)

    dbg.strain, dbg.stress = strain_fit, stress_fit
    
    dyn_modulus, dyn_phase = calculate_dynamic_modulus(stress_fit, strain_fit)
    
    return (dyn_modulus, dyn_phase)

 


# In[14]:

if __name__ == "__main__":
    
    N = 1000 # number of data points
    t = np.linspace(0, 8*np.pi, N)
    
    strain_amp, strain_phase = 1.0, 0.0
    stress_amp, stress_phase = 5.54, -.7

    amp_decay = 1+1*np.exp(-t/2.0)
    # create artificial data with noise
    strain = strain_amp*(amp_decay)*np.sin(t+strain_phase) + 0.5 + np.random.randn(N)
    stress = stress_amp*(amp_decay)*np.sin(t+stress_phase) + 0.5 + np.random.randn(N) 

    fig, (ax1) = plt.subplots(nrows=1, figsize=(12,8))
    
    dbg = DebugData()
    dyn_modulus = fit_data_calculate_dynamic_modulus(t, stress=stress, strain=strain, dbg=dbg)
    
    ax1.plot(t, strain, '.', label='strain')
    ax1.plot(t, stress, '.', label='stress')

    ax1.plot(t, dbg.strain(t), label='fit strain')
    ax1.plot(t, dbg.stress(t), label='fit stress')
    
    ax1.legend()
    
    print("dbg.stress:", dbg.stress.data)
    message = "Fitted Dynamic Modulus: (%5.2f %5.2f)"%dyn_modulus
    message += "\n Orig Dynamic Modulus: (%5.2f %5.2f)"%((stress_amp/strain_amp), (stress_phase-strain_phase))
    message += "\n Fitted Rate: (%5.2f %5.2f)"%(dbg.stress.data.decayAmt  , dbg.stress.data.decayRate )
    fig.text(.45, -.02, message)
    # fig.tight_layout()
    fig.subplots_adjust(hspace=1, )

    plt.show(block=True)
    

# In[12]:




# In[12]:



