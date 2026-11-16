import {validateLot} from './browser-source/candidate-source/app/public/model.js';
export function validateSourceReferenceStock(value){if(!value?.foundationSourceReference&&!value?.sourceIdentityReference)throw Error('A source reference is required.');return validateLot(value);}
