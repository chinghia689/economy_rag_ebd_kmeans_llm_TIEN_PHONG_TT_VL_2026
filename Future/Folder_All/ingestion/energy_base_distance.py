import numpy as np
from scipy.spatial.distance import cdist

def energy_base_distance(X,Y):
    
    X=np.asarray(X)
    Y=np.asarray(Y)
    #Tuong tac cheo
    d_xy=cdist(X,Y,metric='euclidean')
    E_xy=np.mean(d_xy)
    #Tu nang x
    d_xx=cdist(X,X,metric='euclidean')
    E_xx=np.mean(d_xx)
    #Tu nang y
    d_yy=cdist(Y,Y,metric='euclidean')
    E_yy=np.mean(d_yy)
    #Energy_distance
    ED=2*E_xy - E_xx - E_yy

    return max(0,ED)