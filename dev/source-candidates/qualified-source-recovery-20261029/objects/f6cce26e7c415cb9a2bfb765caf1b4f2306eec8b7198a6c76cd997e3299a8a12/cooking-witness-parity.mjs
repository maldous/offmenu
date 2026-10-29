import {preserveCookingWitnesses} from '../public/cooking-witness.js';
export {copyCookingWitness,preserveCookingWitnesses} from '../public/cooking-witness.js';
// Invoke after the existing authenticated state validator, without replacing its
// authorization, revision checks, quantities, history or unrelated normalization.
export function finishCookingWitnessState(input,normalized){
 return {...normalized,profile:preserveCookingWitnesses(input?.profile,normalized.profile||{})};
}
