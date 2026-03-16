import { describe, it, expect } from 'vitest';
import { ApiError, apiError } from './errors';

describe('ApiError', () => {
	it('constructs with simple error detail', () => {
		const err = new ApiError(400, { detail: 'Bad request' });
		expect(err.message).toBe('Bad request');
		expect(err.status).toBe(400);
		expect(err.name).toBe('ApiError');
	});

	it('constructs with validation error detail', () => {
		const err = new ApiError(422, {
			detail: [
				{ loc: ['body', 'name'], msg: 'field required', type: 'value_error' },
				{ loc: ['body', 'email'], msg: 'invalid email', type: 'value_error' },
			],
		});
		expect(err.message).toBe('field required, invalid email');
	});

	it('isValidation returns true for array detail', () => {
		const simple = new ApiError(400, { detail: 'Not found' });
		const validation = new ApiError(422, {
			detail: [{ loc: ['body'], msg: 'required', type: 'value_error' }],
		});
		expect(simple.isValidation()).toBe(false);
		expect(validation.isValidation()).toBe(true);
	});

	it('isConflict returns true for 409', () => {
		expect(new ApiError(409, { detail: 'Conflict' }).isConflict()).toBe(true);
		expect(new ApiError(400, { detail: 'Bad' }).isConflict()).toBe(false);
	});

	it('isNotFound returns true for 404', () => {
		expect(new ApiError(404, { detail: 'Not found' }).isNotFound()).toBe(true);
	});

	it('isForbidden returns true for 403', () => {
		expect(new ApiError(403, { detail: 'Forbidden' }).isForbidden()).toBe(true);
	});
});

describe('apiError factory', () => {
	it('creates ApiError from status and body', () => {
		const err = apiError(500, { detail: 'Internal error' });
		expect(err).toBeInstanceOf(ApiError);
		expect(err.status).toBe(500);
		expect(err.message).toBe('Internal error');
	});
});
