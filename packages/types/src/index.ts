export type HealthService = 'api' | 'worker' | 'ai-service';

export type HealthData<TService extends HealthService = HealthService> = Readonly<{
  status: 'ok';
  service: TService;
}>;

export type PaginationMeta = Readonly<{
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}>;

export type ApiMeta = Readonly<{
  requestId: string;
  pagination?: PaginationMeta;
}>;

export type ApiSuccess<TData> = Readonly<{
  data: TData;
  meta: ApiMeta;
}>;

export type HealthResponse<TService extends HealthService = HealthService> = ApiSuccess<
  HealthData<TService>
>;

export type ValidationIssue = Readonly<{
  path: string;
  code: 'invalid_value';
  message: 'Invalid value';
}>;

export type ProblemDetails = Readonly<{
  type: 'about:blank';
  title: string;
  status: number;
  detail: string;
  instance: string;
  requestId: string;
  errors?: readonly ValidationIssue[];
}>;
