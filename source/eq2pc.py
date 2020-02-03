#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Mauricio Fernández

Github: FIXME

Module for generation and manipulation of 2PC-equivalent structures.

Dependencies
------------
numpy, scipy, glob, os, shutil, datetime, matplotlib, mpl_toolkits

Main usage
-----------
Import module and search for 2PC-equivalanet structures in 2 dimensions
with shape [4,3] and 3 phases with 3 events in phase 1 and 2 events in 
phase 2 (events for remaining phase are computed automatically).

    >>> import eq2pc as e2
    >>> cases = e2.Ceqsearch([4,3],[3,2],b=True) # search for cases and break after first case
    >>> len(cases[0]) # number of 2PC-equivalent structures found in first case
    2
    >>> S1,S2 = cases[0] # extract structures from first case
    >>> print(S1)
    [[1 1 3]
     [2 3 3]
     [3 3 1]
     [2 3 3]]
    >>> print(S2)
    [[1 1 3]
     [3 3 2]
     [3 3 1]
     [3 3 2]]
    >>> e2.Ceq(S1,S2) # check if all 2PC of the structures are identical
    True
    >>> e2.rel(S1,S2) # check if the structures are related by periodic translation or reflections
    False
    
(See also 'demo1_search.py' in Github repository for further examples).

"""

# Computation
import numpy as np
from scipy import signal
from sympy.utilities.iterables import multiset_permutations
import glob, os, shutil, datetime

# Plotting
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Patch

# For custom legend
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

#%% Utilities

def fgrid(d):
    '''
    Flattened grid.
    '''
    n = np.prod(d)
    return np.array(np.unravel_index(range(n),d)).T

def periodic(a):
    '''
    Return periodic extension of array a.
    '''
    nd = np.ndim(a)
    aa = a
    for ax in range(nd):
        aa = np.concatenate([aa,aa],ax)
    return aa

def shift(a,s):
    '''
    Periodic shift of array a by s.
    '''
    return np.roll(a,s,list(range(len(s))))

def zp(a,z):
    '''
    zp(a,z) return the zero-padded array (element-wise and dimension-wise
    depending on vector z)

    Parameters
    ----------
    a : np.array (1,2 or 3-dimensional)
        Array to be zero-padded.
    z : list
        Vector containing the zero-padding patterns.

    Returns
    -------
    out : np.array (1,2 or 3-dimensional)
        Zero-padded array.

    '''
    D = np.ndim(a)
    P = np.array(a.shape)
    N = len(z)
    if N<=D:
        z2 = np.ones_like(P)
        z2[:N] = z
        P_out = z2*P
        out = np.zeros(P_out,dtype=a.dtype)
        if D==1:
            out[::z2[0]] = a
        if D==2:
            out[::z2[0],::z2[1]] = a
        if D==3:
            out[::z2[0],::z2[1],::z2[2]] = a
    else:
        P2 = np.ones_like(z)
        P2[:D] = P
        P_out = z*P2
        out = np.zeros(P_out,dtype=a.dtype)
        if D==1:
            if N==2:
                out[::z[0],0] = a
            if N==3:
                out[::z[0],0,0] = a
        if D==2:
            if N==3:
                out[::z[0],::z[1],0] = a
    return out

#%% Relation

def rel_shift_explicit(a,b,s):
    '''
    Check if arrays a and b are related by the shift s.
    '''
    return np.all(a==shift(b,s))

def rel_shift(a,b):
    '''
    Check if arrays a and b are related by some shift.
    '''
    s = fgrid(a.shape)
    ns = len(s)
    i = 0
    while i < ns:
        out = rel_shift_explicit(a,b,s[i])
        if out: break
        i += 1
    return out

def ref(a,ax):
    '''
    Shortcut for np.flip(a,ax).
    '''
    return np.flip(a,ax)

def rel_ref_shift(a,b):
    '''
    Check if arrays a and b are related by some reflection and shift.
    '''
    nd = np.ndim(a)
    if nd==1:
        ax = (0,)
    if nd==2:
        ax = (0,1,(0,1))
    if nd==3:
        ax = (0,1,2,(0,1),(0,2),(1,2),(0,1,2))
    nax = len(ax)
    i = 0
    while i < nax:
        out = rel_shift(a,ref(b,ax[i]))
        if out: break
        i += 1
    return out
    
def rel(a,b,ref=True):
    '''
    Check if array a and b are related.
    '''
    out = rel_shift(a,b)
    if ref and not out:
        out = rel_ref_shift(a,b)
    return out

def unrel(a,b):
    '''
    Check if arrays a and b are unrelated.
    '''
    return not rel(a,b)

def unrelmax(a,unrel_h=unrel):
    '''
    Extract largest pair-wise unrelated element list a (must be a one-dimensional np.array). 
    '''
    out = np.array([],dtype=type(a[0]))
    while len(a)>0:
        out = np.concatenate([out,[a[0]]])
        a = a[list(map(lambda x: unrel_h(a[0],x),a))]
    return out
    
#%% Basic operations conserving 2PC-equivalence
    
def gS(d,nev,sh=True):
    '''
    Generate structure.
    '''
    ntotal = np.prod(d)
    S = np.zeros(ntotal,dtype=np.int)
    for ph in range(len(nev)):
        S[int(np.sum(nev[:ph])):np.sum(nev[:ph+1])] = ph+1
    if sh: np.random.shuffle(S)
    if np.sum(nev)<ntotal:
        S[S==0] = len(nev)+1
    return S.reshape(d)

def rnev(S):
    '''
    Return number of events.
    '''
    nph = np.max(S)
    return np.array([np.sum(S==i) for i in range(1,nph+1)])

def rS(Is,allI=True):
    '''
    Return structure.
    '''
    if allI:
        # All indicators given
        return np.sum([ii*II for ii,II in zip(range(1,len(Is)+1),Is)],0)
    else:
        # Only linear independent indicators given
        temp = np.sum([ii*II for ii,II in zip(range(1,len(Is)+1),Is)],0)
        temp[temp==0] = len(Is)+1
        return temp
    
def rIs(S,allI=True):
    '''
    Return indicator arrays from S.
    '''
    if allI:
        return 1*np.array([S==i1 for i1 in range(1,np.max(S)+1)])
    else:
        # only linear independent
        return 1*np.array([S==i1 for i1 in range(1,np.max(S))])

def phe(S,z):
    '''
    Phase extension through zero-padding
    '''
    S = zp(S,z)
    S[S==0] = np.max(S)+1
    return S

def ka(S,Ks):
    '''
    Kernel application for an adequately phase extended structure.
    '''
    d = S.shape
    nd = len(d)
    Is = rIs(S,allI=False)
    if len(Ks)<len(Is):
        Kid = np.array((len(Is)-len(Ks))*[np.ones_like(Ks[0])])
        Ks = np.concatenate([Ks,Kid],0)
    if nd==1:
        return rS([signal.convolve(I,K)[:d[0]] for I,K in zip(Is,Ks)],allI=False) 
    if nd==2:
        return rS([signal.convolve(I,K)[:d[0],:d[1]] for I,K in zip(Is,Ks)],allI=False)
    if nd==3:
        return rS([signal.convolve(I,K)[:d[0],:d[1],:d[2]] for I,K in zip(Is,Ks)],allI=False)
    
def se(S,Ks=[]):
    '''
    Structure extension implicitly specified through the dimension of given kernels.
    '''
    if len(Ks)==0:
        D = np.ndim(S)
        if D==1: Ks = [np.array([1,0])]
        if D==2: Ks = [np.array([[1,0],[0,0]])]
        if D==3:
            Ks = [np.zeros([2,2,2],dtype=np.int)]
            Ks[0][0,0,0] = 1
    return ka(phe(S,z=Ks[0].shape),Ks)

def phc(S,c=[[1,2]]):
    '''
    Phase concatenation.
    '''
    ci = []
    for cc in c:
        ci += cc
    ci = set(ci)
    temp = np.sort(list(set(range(1,1+np.max(S))).difference(ci)))
    for i in temp:
        c += [[i]]
    nc = len(c)
    temp = np.copy(S)
    counter = 0
    for i in range(nc):
        counter += 1
        for j in c[i]:
            temp[temp==j] = counter
    return temp

#%% 2PC
    
def rC_s(Ia,Ib,s):
    '''
    Return the 2PC for indicator arrays Ia and Ib and given shift vector s.
    The shift vector, e.g., s = [2,3,0] considers the 2PC by computing 
    Ia[i,j,k]*Ib[i+2,j+3,k+0] and the corresponding sum.
    '''
    return np.sum(Ia*np.roll(Ib,-np.array(s),list(range(len(s)))))

def rC(Ia,Ib,f=False,spec=False):
    '''
    Return the 2PC for all shifts.
    Option f=True: computation with FFT
    Option f=False: exact computation
    '''
    if f:
        if spec:
            return np.conj(np.fft.fftn(Ia))*np.fft.fftn(Ib)
        else:
            return np.real(np.fft.ifftn(np.conj(np.fft.fftn(Ia))*np.fft.fftn(Ib)))
    else:
        dout = np.array(Ia.shape)   
        return np.array([rC_s(Ia,Ib,ss) for ss in fgrid(dout)]).reshape(dout)
    
def rCs(S,allI=False,op=0,f=False,spec=False):
    '''
    Return all 2PC of the given structure S.
    '''
    Is = rIs(S,allI=allI)
    # All independent ones
    if op==0:
        nph = len(Is)
        return np.array([rC(Is[a],Is[b],f=f,spec=spec) for a in range(nph) for b in range(a,nph)])
    # All
    if op==1:
        return np.array([[rC(Ia,Ib,f=f,spec=spec) for Ib in Is] for Ia in Is])
    
#%% 2PC-equivalence
    
def Ceq(S1,S2):
    '''
    Test if structures are 2PC-equivalent.
    '''
    return np.all(rCs(S1)==rCs(S2))

def Ceqsearch(d,nev,b=True,ref=True,f=False,spec=False,tol=1e-13,info=True):
    # Turn off reflection relation if 3d
    if len(d)==3: ref = True
    
    # Generate inidicator arrays
    print('...Generating indicator arrays')
    Ss = gS(d,nev,sh=False).flatten()[1:]
    Ss = np.array(list(multiset_permutations(Ss)))
    nSs = len(Ss)
    Ss = np.hstack([
            np.ones([nSs,1],dtype=np.int)
            ,Ss
            ])
    Ss = Ss.reshape([nSs]+list(d))
    
    # Compute correlations
    print('...Computing correlations')
    temp = rCs(Ss[0],f=f,spec=spec)
    C = np.zeros([nSs]+list(temp.shape))
    C[0] = temp
    for i in range(1,nSs):
        if info:
            print('...Computing correlations - %i / %i = %.4f' % (i+1,nSs,(i+1)/nSs))
        C[i] = rCs(Ss[i],f=f,spec=spec)
    
    # Search for cases
    print('...Searching for cases')
    i = 0
    out = []
    unrelloc = lambda i1,i2: not rel(Ss[i1],Ss[i2],ref)
    while i < nSs:
        if info:
            print('...Searching for cases - %i / %i = %.4f' % (i+1,nSs,(i+1)/nSs))
        Ci = C[i]
        if f:
            cand = np.where([np.linalg.norm(Ci-CC) < tol for CC in C])[0]
        else:
            cand = np.array([j for j in range(i+1,nSs) if np.all(Ci==C[j])])
        if len(cand)>0:
            Si = Ss[i]
            check = [not rel(Si,Ss[c],ref) for c in cand]
            cand = cand[check]
            if len(cand)>0:
                cand = unrelmax(np.array(cand),unrelloc)
                event = np.zeros([1+len(cand)]+d,dtype=np.int)
                event[0] = Si
                for j in range(len(cand)):
                    event[j+1] = Ss[cand[j]]
                out.append(event)
                if type(b)==type(True):
                    if b: break
                if type(b)==type(1):
                    if len(out)==b: break
        i += 1
    if len(out)>1:
        unrelloc = lambda i1,i2: not rel(out[i1][0],out[i2][0],ref)
        cand = unrelmax(np.array(list(range(len(out)))),unrelloc)
        for j in range(1,len(out[0])):
            cand = np.array([c for c in cand if not rel(out[0][j],out[c][0])])
        if len(cand)>1:
            out = [out[c] for c in cand]
        else:
            out = [out[0]]
    print('...Number of structure sets: %i' % len(out))
    return out

def Ceqsave(d,nev,folder='default',info=True):
    if folder=='default':
        folder = 'data/examples/'+str(len(d))+'d_'+'_'.join([str(dd) for dd in d])+'_nev_'+'_'.join([str(dd) for dd in nev])
    t1 = datetime.datetime.now()
    out = Ceqsearch(d,nev,f=False,info=info)
    t2 = datetime.datetime.now()
    
    print(t2-t1)
    if len(out)==0:
        print('NO CASE FOUND!!!!')
    else:
        print('...Case found\n...Saving')
        Ss = out[0]
    
        # Delete old existing folder
        if os.path.exists(folder):
            print('...Deleted old folder')
            shutil.rmtree(folder)
            
        # Create folder
        print('...Created folder')
        os.makedirs(folder)
        
        # Save results
        for i in range(len(Ss)):
        	np.savetxt(folder+'/S%i.dat' % i,Ss[i].flatten(),fmt='%i')

        # Meta
        meta = ['Computation time:\n\t'+str(t2-t1)
                ,'d:\n\t'+str(d)
                ,'nev:\n\t'+str(nev)
                ]
        with open(folder+'/meta.txt','w') as file:
            for item in meta:
                file.write("%s\n" % item)
                
        return folder

def Ceqload(folder,info=True):
    d = folder.split('d_')[1].split('_nev_')[0].split('_')
    d = [int(dd) for dd in d]
    files = np.sort(glob.glob(folder+'/*.dat'))
    S1 = np.loadtxt(files[0],dtype=np.int).reshape(d)
    S2 = np.loadtxt(files[1],dtype=np.int).reshape(d)
    if info:
        plotS(S1)
        plotS(S2)
        print('Are the shown structures related?\n\t%r' % rel(S1,S2,True))
        print('Are the shown structures 2PC-equivalent?\n\t%r' % Ceq(S1,S2))
    return np.array([S1,S2])

def Ceqexamples():
    l = np.sort(glob.glob('data/examples/*'))
    print('Currently available examples:')
    for ll in l: print('\t%s' % ll)
    return l

#%% Plotting

def plotS(S,per=False,fs=(15,15),save='',title=''):
    '''
    Plot structure.
    '''
    colormap = 'hot'
    nph = np.max(S)
    ndim = np.ndim(S)
    if ndim==1:
        plt.figure()
        if not per:
            plt.matshow(
                    np.array([S])
                    ,cmap=plt.get_cmap(colormap,nph)
                    ,vmin=0.5
                    ,vmax=nph+0.5
                    )
        else:
            plt.matshow(
                    periodic(np.array([S]))
                    ,cmap=plt.get_cmap(colormap,nph)
                    ,vmin=0.5
                    ,vmax=nph+0.5
                    )
        plt.yticks([])
        plt.colorbar(ticks=np.arange(1,nph+1))
        if len(save)>0:
            plt.savefig('./'+save+'.png')
        plt.show()
    if ndim==2:
        plt.figure()
        if not per:
            plt.matshow(
                    S
                    ,cmap=plt.get_cmap(colormap,nph)
                    ,vmin=0.5
                    ,vmax=nph+0.5
                    )
        else:
            plt.matshow(
                    periodic(S)
                    ,cmap=plt.get_cmap(colormap,nph)
                    ,vmin=0.5
                    ,vmax=nph+0.5
                    )
        plt.colorbar(ticks=np.arange(1,nph+1))
        if len(save)>0:
            plt.savefig('./'+save+'.png')
        plt.show()
    if ndim==3:
        plt.figure()
        base = plt.cm.get_cmap('hot')
        colors = base(np.linspace(0,1,np.max(S)))
        ax = plt.gca(projection='3d')
        for i in range(1,nph):
            if not per:
                ax.voxels(S==i,facecolors=colors[i-1],edgecolor='gray')
            else:
                ax.voxels(periodic(S==i),facecolors=colors[i-1],edgecolor='gray')
        ax.set_xlabel('$p_1$')
        ax.set_ylabel('$p_2$')
        ax.set_zlabel('$p_3$')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        mylegend = []
        for i in range(1,nph):
            mylegend.append(
                    Patch(
                            label=str(i)
                            ,facecolor=colors[i-1]
                            ,edgecolor='black'
                            )
                    )
        mylegend.append(
                Patch(
                        label=str(nph)
                        ,facecolor='white'
                        ,edgecolor='black'
                        )
                )
        plt.legend(handles=mylegend)
        plt.tight_layout()
        if len(title)>0:
            plt.title(title)
        if len(save)>0:
            plt.savefig('./'+save)
        plt.show()
        
def plotC(C,per=False):
    '''
    Plot 2PC for 1d and 2d structures.
    '''
    if per: C = periodic(C)
    nd = np.ndim(C)
    plt.figure()
    if nd==1:
        plt.matshow(np.array([C]))
    if nd==2:
        plt.matshow(C)
    plt.colorbar()
    plt.show()
