// Fixture 2: a PascalCase file that defines no class of that name.
// The repo's naming rule allows PascalCase only for a file that
// defines one class of the same name; this one only exports helpers,
// so it should be kebab-case (date-utils.js).
export const daysInMonth = (year, month) => {
  return new Date(year, month + 1, 0).getDate();
};

export const isWeekend = (date) => {
  const day = date.getDay();
  return day === 0 || day === 6;
};
