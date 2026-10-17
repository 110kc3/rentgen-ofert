/* Shared decoder for column tables; old regional object arrays remain readable. */
(function (root) {
  "use strict";
  function decode(value) {
    if (Array.isArray(value)) {
      if (value.some(row => !row || typeof row !== "object" || Array.isArray(row)))
        throw Error("Invalid listing rows");
      return value;
    }
    if (!value || value.schema !== 1 || !Array.isArray(value.fields) || !Array.isArray(value.rows))
      throw Error("Unsupported column table");
    const fields = value.fields;
    if (fields.some(key => typeof key !== "string" || !/^[a-z][a-z0-9_]*$/.test(key)
        || key === "constructor" || key === "prototype") || new Set(fields).size !== fields.length)
      throw Error("Invalid column table fields");
    const result = new Array(value.rows.length);
    for (let i = 0; i < value.rows.length; i++) {
      const row = value.rows[i];
      if (!Array.isArray(row) || row.length > fields.length) throw Error("Invalid column table row");
      const record = {};
      for (let j = 0; j < row.length; j++) if (row[j] !== null) record[fields[j]] = row[j];
      result[i] = record;
    }
    return result;
  }
  root.RentgenPayload = { decode };
  if (typeof module !== "undefined" && module.exports) module.exports = root.RentgenPayload;
})(typeof globalThis !== "undefined" ? globalThis : this);
