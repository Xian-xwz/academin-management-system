export function isExternal(path: string) {
  return /^(https?:|mailto:|tel:)/.test(path);
}

export function isValidStudentId(studentId: string) {
  const reg = /^[A-Za-z0-9]{8,20}$/;
  return reg.test(studentId);
}
