import request from '@/api';

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

export const getStudentInfo = async (studentId: string) => {
  const res = await request.get(`/student/${studentId}/academic-info`);
  const data: any = unwrapResponse(res);
  return {
    studentId,
    name: data.baseInfo?.name,
    major: data.baseInfo?.major,
    grade: data.baseInfo?.grade
  };
};

export const getAcademicInfo = async (studentId: string) => {
  const res = await request.get(`/student/${studentId}/academic-info`);
  return unwrapResponse(res);
};
