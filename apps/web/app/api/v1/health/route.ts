import { NextResponse } from 'next/server';
import type { HealthResponse, ProblemDetails } from '@smart-catering/types';
import { createServerApiClient } from '@/lib/api/server';
import { normalizeApiError } from '@/lib/api/client';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const incomingRequestId = request.headers.get('x-request-id');
  const client = createServerApiClient(incomingRequestId);

  try {
    const response = await client.get<HealthResponse>('/api/v1/health');
    return NextResponse.json(response.data, {
      status: response.status,
      headers: {
        'content-type': 'application/json',
        ...(response.headers['x-request-id']
          ? { 'x-request-id': String(response.headers['x-request-id']) }
          : incomingRequestId
            ? { 'x-request-id': incomingRequestId }
            : {}),
      },
    });
  } catch (error) {
    const problem = normalizeApiError(error, '/api/v1/health');
    const safeProblem: ProblemDetails = {
      type: 'about:blank',
      title: 'Service Unavailable',
      status: 503,
      detail: 'Backend API service is not reachable or healthy',
      instance: '/api/v1/health',
      requestId: incomingRequestId || problem.requestId || 'unknown',
    };
    return NextResponse.json(safeProblem, {
      status: 503,
      headers: {
        'content-type': 'application/problem+json',
        'x-request-id': safeProblem.requestId,
      },
    });
  }
}
