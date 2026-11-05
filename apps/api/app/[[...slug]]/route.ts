import { createNotFoundHandler } from '../../lib/index';

export const dynamic = 'force-dynamic';

const notFound = createNotFoundHandler();

export const GET = notFound;
export const HEAD = notFound;
export const POST = notFound;
export const PUT = notFound;
export const PATCH = notFound;
export const DELETE = notFound;
export const OPTIONS = notFound;
