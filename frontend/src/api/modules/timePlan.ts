import request from '@/api';

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

export const getTimePlans = async (params?: any) => {
  const res = await request.get('/time-plan/events', { params });
  return unwrapResponse(res);
};

export const addTimePlan = async (data: any) => {
  const res = await request.post('/time-plan/events', data);
  return unwrapResponse(res);
};

export const updateTimePlan = async (id: number | string, data: any) => {
  const res = await request.put(`/time-plan/events/${id}`, data);
  return unwrapResponse(res);
};

export const deleteTimePlan = async (id: number | string) => {
  const res = await request.delete(`/time-plan/events/${id}`);
  return unwrapResponse(res);
};

export const syncFromSchedule = async (term = '2025-2026-1') => {
  const res = await request.post('/time-plan/sync-from-schedule', null, { params: { term } });
  return unwrapResponse(res);
};
