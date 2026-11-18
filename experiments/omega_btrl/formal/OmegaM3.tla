------------------------------- MODULE OmegaM3 -------------------------------
EXTENDS Naturals
\* MODEL FOR REVIEW, NOT DEPLOYED RUNTIME. TLC not yet run.
\* Signed evidence/roles/revocation are represented only by Boolean abstractions.
VARIABLES sourcePinned, policyPinned, evidenceVerified, revocationFresh,
          reviewIndependent, humanApproved, conflictFree, reviewEligible,
          actionAuthorized
vars == <<sourcePinned, policyPinned, evidenceVerified, revocationFresh,
          reviewIndependent, humanApproved, conflictFree, reviewEligible,
          actionAuthorized>>

Init == /\ sourcePinned = FALSE
        /\ policyPinned = FALSE
        /\ evidenceVerified = FALSE
        /\ revocationFresh = FALSE
        /\ reviewIndependent = FALSE
        /\ humanApproved = FALSE
        /\ conflictFree = FALSE
        /\ reviewEligible = FALSE
        /\ actionAuthorized = FALSE

PinSource == /\ ~sourcePinned
             /\ sourcePinned' = TRUE
             /\ UNCHANGED <<policyPinned, evidenceVerified, revocationFresh,
                             reviewIndependent, humanApproved, conflictFree,
                             reviewEligible, actionAuthorized>>
PinPolicy == /\ sourcePinned /\ ~policyPinned
             /\ policyPinned' = TRUE
             /\ UNCHANGED <<sourcePinned, evidenceVerified, revocationFresh,
                             reviewIndependent, humanApproved, conflictFree,
                             reviewEligible, actionAuthorized>>
VerifyEvidence == /\ sourcePinned /\ policyPinned /\ ~evidenceVerified
                  /\ evidenceVerified' = TRUE
                  /\ UNCHANGED <<sourcePinned, policyPinned, revocationFresh,
                                  reviewIndependent, humanApproved, conflictFree,
                                  reviewEligible, actionAuthorized>>
RefreshRevocations == /\ sourcePinned /\ ~revocationFresh
                      /\ revocationFresh' = TRUE
                      /\ UNCHANGED <<sourcePinned, policyPinned, evidenceVerified,
                                      reviewIndependent, humanApproved, conflictFree,
                                      reviewEligible, actionAuthorized>>
IndependentReview == /\ evidenceVerified /\ revocationFresh /\ ~reviewIndependent
                     /\ reviewIndependent' = TRUE
                     /\ UNCHANGED <<sourcePinned, policyPinned, evidenceVerified,
                                     revocationFresh, humanApproved, conflictFree,
                                     reviewEligible, actionAuthorized>>
HumanApproval == /\ reviewIndependent /\ ~humanApproved
                 /\ humanApproved' = TRUE
                 /\ UNCHANGED <<sourcePinned, policyPinned, evidenceVerified,
                                 revocationFresh, reviewIndependent, conflictFree,
                                 reviewEligible, actionAuthorized>>
ResolveConflict == /\ sourcePinned /\ ~conflictFree
                   /\ conflictFree' = TRUE
                   /\ UNCHANGED <<sourcePinned, policyPinned, evidenceVerified,
                                   revocationFresh, reviewIndependent, humanApproved,
                                   reviewEligible, actionAuthorized>>
Ready == sourcePinned /\ policyPinned /\ evidenceVerified /\ revocationFresh
         /\ reviewIndependent /\ humanApproved /\ conflictFree
OfferReview == /\ Ready /\ ~reviewEligible
               /\ reviewEligible' = TRUE
               /\ UNCHANGED <<sourcePinned, policyPinned, evidenceVerified,
                               revocationFresh, reviewIndependent, humanApproved,
                               conflictFree, actionAuthorized>>
RevokeEvidence == /\ evidenceVerified
                  /\ evidenceVerified' = FALSE
                  /\ humanApproved' = FALSE
                  /\ reviewEligible' = FALSE
                  /\ UNCHANGED <<sourcePinned, policyPinned, revocationFresh,
                                  reviewIndependent, conflictFree, actionAuthorized>>
ExpireRevocations == /\ revocationFresh
                     /\ revocationFresh' = FALSE
                     /\ humanApproved' = FALSE
                     /\ reviewEligible' = FALSE
                     /\ UNCHANGED <<sourcePinned, policyPinned, evidenceVerified,
                                     reviewIndependent, conflictFree, actionAuthorized>>
SupersedeSource == /\ sourcePinned
                   /\ sourcePinned' = FALSE
                   /\ policyPinned' = FALSE
                   /\ evidenceVerified' = FALSE
                   /\ revocationFresh' = FALSE
                   /\ reviewIndependent' = FALSE
                   /\ humanApproved' = FALSE
                   /\ conflictFree' = FALSE
                   /\ reviewEligible' = FALSE
                   /\ UNCHANGED actionAuthorized
SupersedePolicy == /\ policyPinned
                   /\ policyPinned' = FALSE
                   /\ evidenceVerified' = FALSE
                   /\ reviewIndependent' = FALSE
                   /\ humanApproved' = FALSE
                   /\ reviewEligible' = FALSE
                   /\ UNCHANGED <<sourcePinned, revocationFresh, conflictFree,
                                   actionAuthorized>>
WithdrawReview == /\ reviewIndependent
                  /\ reviewIndependent' = FALSE
                  /\ humanApproved' = FALSE
                  /\ reviewEligible' = FALSE
                  /\ UNCHANGED <<sourcePinned, policyPinned, evidenceVerified,
                                  revocationFresh, conflictFree, actionAuthorized>>
WithdrawApproval == /\ humanApproved
                    /\ humanApproved' = FALSE
                    /\ reviewEligible' = FALSE
                    /\ UNCHANGED <<sourcePinned, policyPinned, evidenceVerified,
                                    revocationFresh, reviewIndependent, conflictFree,
                                    actionAuthorized>>
Next == PinSource \/ PinPolicy \/ VerifyEvidence \/ RefreshRevocations
        \/ IndependentReview \/ HumanApproval \/ ResolveConflict \/ OfferReview
        \/ RevokeEvidence \/ ExpireRevocations \/ SupersedeSource
        \/ SupersedePolicy \/ WithdrawReview \/ WithdrawApproval

Spec == Init /\ [][Next]_vars
TypeOK == /\ sourcePinned \in BOOLEAN /\ policyPinned \in BOOLEAN
          /\ evidenceVerified \in BOOLEAN /\ revocationFresh \in BOOLEAN
          /\ reviewIndependent \in BOOLEAN /\ humanApproved \in BOOLEAN
          /\ conflictFree \in BOOLEAN /\ reviewEligible \in BOOLEAN
          /\ actionAuthorized \in BOOLEAN
NoBypass == reviewEligible => Ready
NeverGrantAction == actionAuthorized = FALSE
=============================================================================
