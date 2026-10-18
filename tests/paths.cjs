// Keep generated browser screenshots out of the source root and publishing tree.
const fs=require('fs'),path=require('path');
exports.preview=name=>{
 if(path.basename(name)!==name)throw Error('Use a screenshot filename only.');
 const directory=path.resolve(__dirname,'../previews/website');
 fs.mkdirSync(directory,{recursive:true});return path.join(directory,name);
};
