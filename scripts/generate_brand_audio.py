import math, wave, random
from pathlib import Path
R=44100
import sys
out=Path(sys.argv[1] if len(sys.argv)>1 else 'build')
out.mkdir(parents=True,exist_ok=True)
def render(name, notes, duration, mood):
    rng=random.Random(914)
    a=[0.0]*int(R*duration)
    for start,freq,length,amp in notes:
        for j in range(int(R*length)):
            k=int(start*R)+j
            if k>=len(a): break
            t=j/R
            attack=min(1,t/.018)
            release=min(1,max(0,(length-t)/.14))
            env=attack*release*math.exp(-t*(2.4 if mood=='chat' else 1.5))
            v=math.sin(2*math.pi*freq*t)
            v+=.26*math.sin(2*math.pi*freq*2.003*t)*math.exp(-t*3)
            v+=.11*math.sin(2*math.pi*freq*3*t)*math.exp(-t*5)
            a[k]+=amp*env*v
    if mood=='cinema':
        for j in range(min(len(a),int(R*.6))):
            t=j/R
            a[j]+=.22*math.sin(2*math.pi*(62*t+25*.09*(1-math.exp(-t/.09))))*math.exp(-t*8)*min(1,t/.012)
    if mood=='mystery':
        for j in range(int(R*.48)):
            t=j/R
            a[j]+=.025*(rng.random()*2-1)*math.sin(math.pi*t/.48)**2
    left=a.copy();right=a.copy()
    for delay,gain in [(.073,.18),(.137,.13),(.229,.09),(.347,.055)]:
        n=int(delay*R)
        for j in range(n,len(a)):
            left[j]+=a[j-n]*gain
            right[j]+=a[j-max(1,n-331)]*gain
    peak=max(max(map(abs,left)),max(map(abs,right)),.01)
    scale=.72/peak
    import array
    samples=array.array('h')
    for i,(l,r) in enumerate(zip(left,right)):
        fade=min(1,i/(R*.008),(len(a)-1-i)/(R*.12))
        samples.extend((int(l*scale*fade*32767),int(r*scale*fade*32767)))
    p=out/(name+'.wav')
    with wave.open(str(p),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(R);w.writeframes(samples.tobytes())
    return p
notes=[(0,146.83,1.1,.27),(.12,293.66,1.2,.2),(.48,440,1.2,.23),(.79,587.33,1.5,.27),(.8,369.99,1.4,.12)]
render('brand-intro',notes,2.8,'cinema')
closing=[(0,notes[-1][1],.85,.20),(.24,notes[1][1],1.1,.15),(.49,notes[0][1]*2,1.4,.22)]
render('brand-outro',closing,2.5,'cinema')
