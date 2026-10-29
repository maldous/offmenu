import test from 'node:test';
import assert from 'node:assert/strict';
import {cleanCommunityRecipe,cleanCommunityProfile,COMMUNITY_LICENSES} from '../../apps/web/src/recipe-community-model.js';
test('community model only accepts structured licensed recipes and opt-in profiles',()=>{assert.deepEqual(COMMUNITY_LICENSES,['CC BY 4.0','CC0-1.0']);assert.throws(()=>cleanCommunityRecipe({title:''}));assert.deepEqual(cleanCommunityProfile({alias:'Cook',bio:'',published:true}),{alias:'Cook',bio:'',published:true});assert.throws(()=>cleanCommunityProfile({alias:'x',bio:'',published:true}));});
