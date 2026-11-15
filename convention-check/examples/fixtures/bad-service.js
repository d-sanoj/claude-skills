// Fixture 1: every violation is deliberate. A new service file that
// breaks three conventions at once: var instead of const, a double
// quoted string with no apostrophe, and a console.log in apps/ code.
var cache = {};
var hits = 0;

export function lookup(key) {
  console.log("looking up " + key);
  if (cache[key]) {
    hits = hits + 1;
    return cache[key];
  }
  return null;
}
