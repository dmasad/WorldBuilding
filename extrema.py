import numpy as np

def get_minima(data):
    min_pts = []
    for i in range(1, len(data)-1):
        if data[i-1] > data[i] < data[i+1]:
            min_pts.append(i)
    return min_pts

def get_maxima(data):
    max_pts = []
    for i in range(1, len(data)-1):
        if data[i-1] < data[i] > data[i+1]:
            max_pts.append(i)
    return max_pts

def get_window(i, data, extrema_type="min"):
    min_win = lambda x: max(0, i-x)
    max_win = lambda x: min(len(data), i+x)
    if extrema_type == "min":
        argcheck = lambda d: np.any(data[min_win(d):max_win(d)] < data[i])
    elif extrema_type == "max":
        argcheck = lambda d: np.any(data[min_win(d):max_win(d)] > data[i])
    max_d = np.floor_divide(len(data), 2)
    for d in range(1, max_d):
        if argcheck(d):
            return d
    else:
        return d

def rank_extrema(data):
    '''
    Get the local extrema and the window for each.
    '''

    min_pts = {x: get_window(x, data, "min") for x in get_minima(data)}
    max_pts = {x: get_window(x, data, "max") for x in get_maxima(data)}
    return {"min": min_pts, "max": max_pts}

