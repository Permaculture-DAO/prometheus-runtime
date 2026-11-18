"""Standalone explicit finite-state reachability checker for OmegaM3 abstraction.

This is an independent Python transition checker, NOT TLC/Apalache/Tamarin.
The abstraction intentionally does not model signatures, key custody, physical
truth, cross-language canonical serialization, or real authorization.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, replace
import json

@dataclass(frozen=True)
class State:
    sourcePinned: bool = False
    policyPinned: bool = False
    evidenceVerified: bool = False
    revocationFresh: bool = False
    reviewIndependent: bool = False
    humanApproved: bool = False
    conflictFree: bool = False
    reviewEligible: bool = False
    actionAuthorized: bool = False

    @property
    def ready(self) -> bool:
        return all((self.sourcePinned, self.policyPinned, self.evidenceVerified,
                    self.revocationFresh, self.reviewIndependent,
                    self.humanApproved, self.conflictFree))


def transitions(s: State, mutant: bool = False) -> list[tuple[str, State]]:
    out = []
    def add(name, condition, **updates):
        if condition:
            out.append((name, replace(s, **updates)))
    add('PinSource', not s.sourcePinned, sourcePinned=True)
    add('PinPolicy', s.sourcePinned and not s.policyPinned, policyPinned=True)
    add('VerifyEvidence', s.sourcePinned and s.policyPinned and not s.evidenceVerified,
        evidenceVerified=True)
    add('RefreshRevocations', s.sourcePinned and not s.revocationFresh,
        revocationFresh=True)
    add('IndependentReview', s.evidenceVerified and s.revocationFresh and not s.reviewIndependent,
        reviewIndependent=True)
    add('HumanApproval', s.reviewIndependent and not s.humanApproved,
        humanApproved=True)
    add('ResolveConflict', s.sourcePinned and not s.conflictFree, conflictFree=True)
    add('OfferReview', s.ready and not s.reviewEligible, reviewEligible=True)
    add('RevokeEvidence', s.evidenceVerified, evidenceVerified=False,
        humanApproved=False, **({} if mutant else {'reviewEligible':False}))
    add('ExpireRevocations', s.revocationFresh, revocationFresh=False,
        humanApproved=False, reviewEligible=False)
    add('SupersedeSource', s.sourcePinned, sourcePinned=False, policyPinned=False,
        evidenceVerified=False, revocationFresh=False, reviewIndependent=False,
        humanApproved=False, conflictFree=False, reviewEligible=False)
    add('SupersedePolicy', s.policyPinned, policyPinned=False,
        evidenceVerified=False, reviewIndependent=False, humanApproved=False,
        reviewEligible=False)
    add('WithdrawReview', s.reviewIndependent, reviewIndependent=False,
        humanApproved=False, reviewEligible=False)
    add('WithdrawApproval', s.humanApproved, humanApproved=False,
        reviewEligible=False)
    return out


def violation(s: State) -> str | None:
    if s.reviewEligible and not s.ready:
        return 'NO_BYPASS_VIOLATION'
    if s.actionAuthorized:
        return 'ACTION_AUTHORITY_VIOLATION'
    return None


def check(mutant: bool = False) -> dict:
    initial = State()
    queue = deque([initial])
    discovered = {initial}
    parent: dict[State, tuple[State, str]] = {}
    edge_count = 0
    while queue:
        s = queue.popleft()
        problem = violation(s)
        if problem:
            trace=[]
            cursor=s
            while cursor in parent:
                prev,action=parent[cursor]
                trace.append({'transition': action, 'state': cursor.__dict__})
                cursor=prev
            trace.reverse()
            return {'status':'COUNTEREXAMPLE_FOUND','problem':problem,
                    'visited_states':len(discovered),'explored_edges':edge_count,
                    'trace':trace,'independent_tool':'Python explicit-state enumeration; NOT TLC'}
        for name, nxt in transitions(s, mutant=mutant):
            edge_count += 1
            if nxt not in discovered:
                discovered.add(nxt)
                parent[nxt] = (s,name)
                queue.append(nxt)
    return {'status':'NO_COUNTEREXAMPLE_IN_FINITE_ABSTRACTION',
            'visited_states':len(discovered),'explored_edges':edge_count,
            'properties':['reviewEligible => all seven preconditions',
                          'actionAuthorized = false'],
            'independent_tool':'Python explicit-state enumeration; NOT TLC'}


if __name__ == '__main__':
    a=check(False)
    b=check(True)
    print(json.dumps({'expected_model':a, 'deliberately_mutated_model':b}, indent=2))
    if a['status']!='NO_COUNTEREXAMPLE_IN_FINITE_ABSTRACTION' or b['status']!='COUNTEREXAMPLE_FOUND':
        raise SystemExit(1)
