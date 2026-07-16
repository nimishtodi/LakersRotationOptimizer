
"""Lakers rotation optimizer.

This script contains actual optimization logic:
- validation and scoring for any 48-minute rotation
- randomized free-minute local search
- optional exact segment-grid MILP solve with scipy.optimize.milp

Run examples:
    python optimizer.py
    python optimizer.py --mode local --iterations 200000 --seed 7
    python optimizer.py --mode milp-segment --time-limit 120
"""
from __future__ import annotations
import argparse, csv, json, math, random
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent

def norm(lineup: str | Iterable[str]) -> str:
    if isinstance(lineup, str):
        return "/".join(sorted(p.strip() for p in lineup.split("/")))
    return "/".join(sorted(p.strip() for p in lineup))

def load_ratings(path: Path) -> Dict[str,float]:
    out = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if row.get("include_in_optimizer", "true").lower() == "true":
                out[row["normalized_lineup"]] = float(row["rating"])
    return out

def load_rotation(path: Path) -> List[Tuple[int,int,str]]:
    with path.open(newline="") as f:
        return [(int(r["start_minute"]), int(r["end_minute"]), r["lineup"]) for r in csv.DictReader(f)]

def load_constraints(path: Path) -> dict:
    return json.loads(path.read_text())

class RotationModel:
    def __init__(self, ratings: Dict[str,float], constraints: dict):
        self.ratings = ratings
        self.constraints = constraints
        self.players = sorted({p for key in ratings for p in key.split("/")})
        self.max_minutes = constraints["minute_caps"]
        self.min_minutes = {p:0 for p in self.players}
        self.min_minutes.update(constraints.get("minimum_minutes", {}))
        self.half_caps = {p: math.ceil(self.max_minutes[p] / 2) + 1 for p in self.players}
        self.max_stint = {p: constraints["max_stint_default"] for p in self.players}
        self.max_stint.update(constraints.get("max_stint_overrides", {}))
        self.banned_starters = set(constraints["starter_rules"]["cannot_include"])
        self.starter_must_include = set(constraints["starter_rules"]["must_include"])
        self.starter_min_rating = constraints["starter_rules"]["minimum_rating"]
        self.closing = norm(constraints["closing_lineup"])

    def rating(self, lineup: str) -> float:
        return self.ratings[norm(lineup)]

    def score_rotation(self, rotation: List[Tuple[int,int,str]]) -> float:
        return sum((b-a)*self.rating(l) for a,b,l in rotation) / 48.0

    def expand(self, rotation: List[Tuple[int,int,str]]) -> List[str]:
        out = [None] * 48
        for a,b,lineup in rotation:
            for t in range(a,b):
                out[t] = norm(lineup)
        if any(x is None for x in out):
            raise ValueError("rotation does not cover all 48 minutes")
        return out

    def compress(self, minute_lineups: List[str]) -> List[Tuple[int,int,str]]:
        out=[]; start=0; cur=minute_lineups[0]
        for t in range(1,48):
            if minute_lineups[t] != cur:
                out.append((start,t,cur)); start=t; cur=minute_lineups[t]
        out.append((start,48,cur))
        return out

    def score_minutes(self, minute_lineups: List[str]) -> float:
        return sum(self.ratings[l] for l in minute_lineups) / 48.0

    def validate_minutes(self, minute_lineups: List[str]) -> List[str]:
        errors=[]
        on={p:[False]*48 for p in self.players}
        for t,lineup in enumerate(minute_lineups):
            for p in lineup.split('/'):
                on[p][t] = True
        starter=set(minute_lineups[0].split('/'))
        if self.ratings[minute_lineups[0]] < self.starter_min_rating:
            errors.append('starter rating below minimum')
        if not self.starter_must_include.issubset(starter):
            errors.append('starter missing required player')
        if starter & self.banned_starters:
            errors.append('starter includes banned starter')
        for t in list(range(0,5)) + list(range(24,29)):
            if set(minute_lineups[t].split('/')) != starter:
                errors.append('same starters both halves violated')
                break
        for t in range(44,48):
            if minute_lineups[t] != self.closing:
                errors.append('closing lineup violated')
                break
        for hs,he in [(0,24),(24,48)]:
            start=hs; cur=minute_lineups[hs]
            for t in range(hs+1,he):
                if minute_lineups[t] != cur:
                    if t-start < self.constraints['lineup_min_segment']:
                        errors.append(f'lineup segment under minimum at {start}-{t}')
                    start=t; cur=minute_lineups[t]
            if he-start < self.constraints['lineup_min_segment']:
                errors.append(f'lineup segment under minimum at {start}-{he}')
        used=0
        for p in self.players:
            total=sum(on[p])
            if total>0: used += 1
            if total < self.min_minutes.get(p,0): errors.append(f'{p} below min minutes')
            if total > self.max_minutes[p]: errors.append(f'{p} above max minutes')
            for hs,he in [(0,24),(24,48)]:
                if sum(on[p][hs:he]) > self.half_caps[p]: errors.append(f'{p} exceeds half cap')
                t=hs
                while t<he:
                    val=on[p][t]; j=t
                    while j<he and on[p][j]==val: j+=1
                    d=j-t
                    if val:
                        if d < self.constraints['player_min_stint']:
                            errors.append(f'{p} stint under minimum at {t}-{j}')
                        if d > self.max_stint[p]:
                            errors.append(f'{p} stint over max at {t}-{j}')
                        if d == self.max_stint[p] and j < he:
                            k=j
                            while k<he and not on[p][k]: k+=1
                            if k<he and k-j < self.constraints['max_stint_recovery_minutes']:
                                errors.append(f'{p} returns too soon after max stint')
                        if d == self.max_stint[p] and t > hs:
                            k=t-1
                            while k>=hs and not on[p][k]: k-=1
                            if k>=hs and t-k-1 < self.constraints['max_stint_recovery_minutes']:
                                errors.append(f'{p} lacked rest before max stint')
                    else:
                        if t>hs and j<he and d < self.constraints['minimum_rest_minutes']:
                            errors.append(f'{p} rest under minimum at {t}-{j}')
                    t=j
        if used < self.constraints['rotation_size_min'] or used > self.constraints['rotation_size_max']:
            errors.append('rotation size outside bounds')
        return errors

    def is_valid(self, minute_lineups: List[str]) -> bool:
        return len(self.validate_minutes(minute_lineups)) == 0

    def local_search(self, seed_rotation: List[Tuple[int,int,str]], iterations=100_000, seed=1) -> Tuple[float,List[str]]:
        random.seed(seed)
        current=self.expand(seed_rotation)
        errors=self.validate_minutes(current)
        if errors:
            raise ValueError('seed rotation invalid: ' + '; '.join(errors))
        best=current[:]; best_score=self.score_minutes(best)
        cur=current[:]; cur_score=best_score
        candidates=list(self.ratings.keys())
        top=sorted(candidates, key=lambda l:self.ratings[l], reverse=True)
        for it in range(iterations):
            trial=cur[:]
            if random.random()<0.55:
                segments=self.compress(cur)
                a,b,_=random.choice(segments); start,end=a,b
            else:
                hs,he=random.choice([(0,24),(24,44)])
                start=random.randint(hs,he-2)
                length=random.choice([2,3,4,5,6,7,8,9,10,11,12])
                end=min(he,start+length)
                if end-start<2: continue
            replacement=random.choice(top[:45] if random.random()<0.92 else candidates)
            for t in range(start,end): trial[t]=replacement
            if not self.is_valid(trial): continue
            score=self.score_minutes(trial)
            temp=max(0.003, 0.20*(1-it/max(1,iterations)))
            if score>cur_score or random.random()<math.exp((score-cur_score)/temp):
                cur,cur_score=trial,score
                if score>best_score:
                    best,best_score=trial[:],score
        return best_score,best

    def milp_segment_solve(self, segments: List[Tuple[int,int]], time_limit=120, mip_gap=0.01):
        """Exact MILP over a segment grid. Requires scipy.

        This is faster than full minute-level MILP and useful for reproducing the segment-grid experiments.
        """
        import numpy as np
        from scipy.optimize import milp, LinearConstraint, Bounds
        from scipy.sparse import lil_matrix, vstack
        lineups=list(self.ratings.keys())
        L=len(lineups); S=len(segments); P=len(self.players); durs=[b-a for a,b in segments]
        inc=np.zeros((P,L), dtype=int)
        for li,l in enumerate(lineups):
            ps=set(l.split('/'))
            for pi,p in enumerate(self.players): inc[pi,li]=int(p in ps)
        n=L*S+P
        def x(li,s): return li*S+s
        def uid(pi): return L*S+pi
        c=np.zeros(n)
        for li,l in enumerate(lineups):
            for s,d in enumerate(durs): c[x(li,s)] = -self.ratings[l]*d
        rows=[]; lb=[]; ub=[]
        def add(co,lo,hi):
            row=lil_matrix((1,n))
            for k,v in co.items():
                if abs(v)>1e-12: row[0,k]=v
            rows.append(row.tocsr()); lb.append(lo); ub.append(hi)
        for s in range(S): add({x(li,s):1 for li in range(L)},1,1)
        for pi,p in enumerate(self.players):
            co={}
            for li in range(L):
                if inc[pi,li]:
                    for s,d in enumerate(durs): co[x(li,s)]=d
            add(co,self.min_minutes.get(p,0),self.max_minutes[p])
            add({x(li,s):durs[s] for li in range(L) if inc[pi,li] for s,(a,b) in enumerate(segments) if b<=24}, -np.inf, self.half_caps[p])
            add({x(li,s):durs[s] for li in range(L) if inc[pi,li] for s,(a,b) in enumerate(segments) if a>=24}, -np.inf, self.half_caps[p])
            co2=co.copy(); co2[uid(pi)] = -48; add(co2,-np.inf,0)
            co3=co.copy(); co3[uid(pi)] = -1; add(co3,0,np.inf)
        add({uid(pi):1 for pi in range(P)}, self.constraints['rotation_size_min'], self.constraints['rotation_size_max'])
        # eligible starters at segment 0 and first segment of second half
        second_half_start=[i for i,(a,b) in enumerate(segments) if a==24][0]
        eligible=[]
        for li,l in enumerate(lineups):
            ps=set(l.split('/'))
            if (self.ratings[l] >= self.starter_min_rating and self.starter_must_include.issubset(ps) and not (ps & self.banned_starters)):
                eligible.append(li)
        add({x(li,0):1 for li in eligible},1,1)
        add({x(li,second_half_start):1 for li in eligible},1,1)
        for li in range(L): add({x(li,0):1, x(li,second_half_start):-1},0,0)
        best=lineups.index(self.closing)
        add({x(best,S-1):1},1,1)
        # max consecutive approximated by segment windows
        for pi,p in enumerate(self.players):
            m=self.max_stint[p]
            halves=[[i for i,(a,b) in enumerate(segments) if b<=24],[i for i,(a,b) in enumerate(segments) if a>=24]]
            for half in halves:
                for ii,start_s in enumerate(half):
                    total=0
                    for end_s in half[ii:]:
                        total += durs[end_s]
                        if total>m:
                            co={}
                            for s in range(start_s,end_s+1):
                                for li in range(L):
                                    if inc[pi,li]: co[x(li,s)]=co.get(x(li,s),0)+1
                            add(co,-np.inf,(end_s-start_s+1)-1)
                            break
        A=vstack(rows).tocsr()
        res=milp(c, integrality=np.ones(n), bounds=Bounds(0,1), constraints=LinearConstraint(A, np.array(lb), np.array(ub)), options={'time_limit':time_limit,'mip_rel_gap':mip_gap})
        if res.x is None:
            return None
        chosen=[]
        for s in range(S):
            li=max(range(L), key=lambda k: res.x[x(k,s)])
            chosen.append((segments[s][0], segments[s][1], lineups[li].replace('/', '/')))
        return chosen

def print_rotation(model: RotationModel, rotation: List[Tuple[int,int,str]]):
    print(f'Projected net rating: {model.score_rotation(rotation):.3f}')
    for a,b,l in rotation:
        print(f'{a:02d}-{b:02d} ({b-a}): {l:55s} {model.rating(l):6.2f}')
    errors=model.validate_minutes(model.expand(rotation))
    print('Validation:', 'passed' if not errors else 'failed')
    for e in errors: print('-', e)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['validate','local','milp-segment'], default='validate')
    parser.add_argument('--iterations', type=int, default=100000)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--time-limit', type=int, default=120)
    args=parser.parse_args()
    ratings=load_ratings(ROOT/'lineup_ratings_active.csv')
    constraints=json.loads((ROOT/'constraints.json').read_text())
    model=RotationModel(ratings,constraints)
    rotation=load_rotation(ROOT/'current_rotation.csv')
    print(f'Loaded {len(ratings)} active lineups')
    if args.mode=='validate':
        print_rotation(model, rotation)
    elif args.mode=='local':
        score, minutes = model.local_search(rotation, iterations=args.iterations, seed=args.seed)
        best=model.compress(minutes)
        print_rotation(model, best)
    elif args.mode=='milp-segment':
        segments=[(0,5),(5,7),(7,9),(9,12),(12,16),(16,20),(20,24),(24,29),(29,31),(31,33),(33,36),(36,40),(40,42),(42,44),(44,48)]
        result=model.milp_segment_solve(segments, time_limit=args.time_limit)
        if result is None:
            print('MILP did not return a feasible result')
        else:
            print_rotation(model, result)

if __name__=='__main__':
    main()
