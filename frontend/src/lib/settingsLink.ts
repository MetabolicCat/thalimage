/** The Settings link, carrying the page to return to (none from Settings itself). */
export function settingsHref(url: URL): string {
	if (url.pathname === '/settings') return '/settings';
	return `/settings?returnTo=${encodeURIComponent(url.pathname + url.search)}`;
}

/**
 * The page Settings' Close link goes back to: a path on this origin, or `/`.
 * A `returnTo` from the query string is attacker-controlled, so refuse
 * anything that is not a single-slash absolute path (including
 * protocol-relative `//host` and `/\host`), or that resolves off-origin.
 */
export function returnToHref(url: URL): string {
	const raw = url.searchParams.get('returnTo');
	if (!raw || !raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/\\')) return '/';

	let target: URL;
	try {
		target = new URL(raw, url.origin);
	} catch {
		return '/';
	}
	if (target.origin !== url.origin) return '/';
	return target.pathname + target.search + target.hash;
}
