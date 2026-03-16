interface ApiErrorSimple {
	detail: string;
}

interface ApiErrorValidation {
	detail: Array<{ loc: (string | number)[]; msg: string; type: string }>;
}

type ApiErrorBody = ApiErrorSimple | ApiErrorValidation;

export class ApiError extends Error {
	constructor(
		readonly status: number,
		readonly body: ApiErrorBody
	) {
		const message =
			typeof body.detail === 'string'
				? body.detail
				: body.detail.map((e) => e.msg).join(', ');
		super(message);
		this.name = 'ApiError';
	}

	isValidation(): boolean {
		return Array.isArray(this.body.detail);
	}

	isConflict(): boolean {
		return this.status === 409;
	}

	isNotFound(): boolean {
		return this.status === 404;
	}

	isForbidden(): boolean {
		return this.status === 403;
	}
}

/**
 * Extract an ApiError from an openapi-fetch response.
 * Usage: const { data, error } = await client.GET(...);
 *        if (error) throw apiError(response.status, error);
 */
export function apiError(status: number, body: unknown): ApiError {
	return new ApiError(status, body as ApiErrorBody);
}
