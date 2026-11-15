// Fixture 3: clean by every hard rule — const, single quotes,
// kebab-case name, no logging — but it uses one double-quoted
// string. That is advisory only: the checker reports it and still
// exits 0, because double quotes cluster in template and data
// strings and a regex cannot tell those apart from real drift.
export const greet = (name) => {
  const label = "hello";
  return label + ', ' + name;
};
