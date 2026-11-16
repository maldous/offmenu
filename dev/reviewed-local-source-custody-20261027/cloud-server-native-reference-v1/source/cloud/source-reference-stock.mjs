// Private stock annotations use the same strict reference validators as the
// selected browser source. They do not grant source admission or qualification.
import {validateLot} from '../public/model.js';
export function validateSourceReferenceStock(value){
 if(!value?.foundationSourceReference&&!value?.sourceIdentityReference)throw Error('A source reference is required.');
 return validateLot(value);
}
