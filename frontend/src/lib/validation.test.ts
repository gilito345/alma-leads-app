import { describe, expect, it } from "vitest";

import { formatBytes, MAX_RESUME_BYTES, validateLeadForm, type LeadFormInput } from "./validation";

const valid: LeadFormInput = {
  first_name: "Ada",
  last_name: "Lovelace",
  email: "ada@example.com",
  resume: { name: "cv.pdf", size: 2048 },
};

describe("validateLeadForm", () => {
  it("accepts a complete form", () => {
    expect(validateLeadForm(valid)).toEqual({});
  });

  it("requires every field", () => {
    const errors = validateLeadForm({ first_name: " ", last_name: "", email: "", resume: null });
    expect(Object.keys(errors).sort()).toEqual(["email", "first_name", "last_name", "resume"]);
  });

  it("rejects malformed emails", () => {
    expect(validateLeadForm({ ...valid, email: "ada@" }).email).toBeDefined();
  });

  it.each(["cv.txt", "cv", "cv.pdf.exe"])("rejects %s", (name) => {
    expect(validateLeadForm({ ...valid, resume: { name, size: 10 } }).resume).toBeDefined();
  });

  it.each(["cv.PDF", "cv.doc", "my.cv.docx"])("accepts %s", (name) => {
    expect(validateLeadForm({ ...valid, resume: { name, size: 10 } }).resume).toBeUndefined();
  });

  it("rejects files over the size limit", () => {
    const resume = { name: "cv.pdf", size: MAX_RESUME_BYTES + 1 };
    expect(validateLeadForm({ ...valid, resume }).resume).toMatch(/10 MB/);
  });

  it("rejects empty files", () => {
    expect(validateLeadForm({ ...valid, resume: { name: "cv.pdf", size: 0 } }).resume).toBeDefined();
  });
});

describe("formatBytes", () => {
  it("picks a readable unit", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});
