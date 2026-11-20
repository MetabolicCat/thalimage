<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		addCollectionImages,
		archiveImages,
		createTag,
		deleteImages,
		getImageCopies,
		listSources,
		listTags,
		moveCopies,
		removeCollectionImages,
		tagImages,
		untagImages
	} from '$lib/api';
	import { deletionFailures, moveFailures } from '$lib/imageCopies';
	import type { ImageSelection } from '$lib/imageSelection.svelte';
	import { movableTargets, sourceName } from '$lib/sourceTargets';
	import { collectionsStore } from '$lib/stores';
	import type { ImageCopy, Source, Tag } from '$lib/types';
	import DeleteDialog from './DeleteDialog.svelte';
	import MoveDialog from './MoveDialog.svelte';

	/** `archived`: the grid lists archived images, so they can be unarchived.
	 * `collectionId`: the manual collection browsed, which images can leave.
	 * `sourceId`: the source preset browsed, whose files can move elsewhere.
	 * `ondone` runs after an action applied, for the grid to reload. */
	let {
		selection,
		archived = false,
		collectionId,
		sourceId,
		ondone
	}: {
		selection: ImageSelection;
		archived?: boolean;
		collectionId?: number;
		sourceId?: number;
		ondone: () => void;
	} = $props();

	type Picker = 'tag' | 'untag' | 'collection' | 'move';

	let picker = $state<Picker | null>(null);
	let query = $state('');
	let tags = $state<Tag[]>([]);
	let busy = $state(false);
	let error = $state<string | null>(null);
	let debounce: ReturnType<typeof setTimeout> | null = null;
	// The copies confirmed for deletion; null when not deleting.
	let deleting = $state<{ copies: ImageCopy[]; message: string } | null>(null);
	// A delete that left some files removed others: the grid must reload.
	let deletedSome = false;
	// The sources a move can choose between, and the move confirmed.
	let sources = $state<Source[]>([]);
	let moving = $state<{ to: Source; copies: ImageCopy[]; message: string } | null>(null);

	const none = $derived(selection.count === 0);
	const moveTargets = $derived(movableTargets(sources, sourceId ?? -1));
	const fromSource = $derived(sources.find((s) => s.id === sourceId));
	const targets = $derived(
		$collectionsStore.filter(
			(c) =>
				c.type === 'manual' &&
				c.id !== collectionId &&
				c.name.toLowerCase().includes(query.trim().toLowerCase())
		)
	);

	function open(which: Picker) {
		if (picker === which) {
			picker = null;
			return;
		}
		picker = which;
		query = '';
		tags = [];
		error = null;
	}

	async function openMove() {
		open('move');
		if (picker !== 'move') return;
		try {
			sources = await listSources();
		} catch (e) {
			error = e instanceof Error ? e.message : 'The sources could not be read';
		}
	}

	function onQuery() {
		if (picker === 'collection' || picker === 'move') return;
		if (debounce) clearTimeout(debounce);
		const q = query.trim();
		if (!q) {
			tags = [];
			return;
		}
		debounce = setTimeout(async () => {
			tags = await listTags(q);
		}, 200);
	}

	async function run(action: (hashes: string[]) => Promise<unknown>) {
		busy = true;
		error = null;
		try {
			await action(selection.hashes);
			picker = null;
			// Counts in the sidebar change with what an action does.
			collectionsStore.refresh();
			ondone();
		} catch (e) {
			error = e instanceof Error ? e.message : 'The action failed';
		} finally {
			busy = false;
		}
	}

	function applyTag(tag: Tag) {
		const untag = picker === 'untag';
		run((hashes) => (untag ? untagImages(tag.id, hashes) : tagImages(tag.id, hashes)));
	}

	function onQueryKeydown(e: KeyboardEvent) {
		if (e.key !== 'Enter' || !query.trim() || (picker !== 'tag' && picker !== 'untag')) return;
		e.preventDefault();
		const name = query.trim();
		const existing = tags.find((t) => t.name.toLowerCase() === name.toLowerCase());
		if (existing) applyTag(existing);
		else if (picker === 'tag') run(async (hashes) => tagImages((await createTag(name)).id, hashes));
	}

	/** Every copy of these images; an image already gone has none. */
	async function copiesOf(hashes: string[]): Promise<ImageCopy[]> {
		const copies = await Promise.all(hashes.map((h) => getImageCopies(h).catch(() => [])));
		return copies.flat();
	}

	async function askDelete() {
		picker = null;
		busy = true;
		error = null;
		try {
			deleting = { copies: await copiesOf(selection.hashes), message: '' };
		} finally {
			busy = false;
		}
	}

	async function confirmDelete() {
		if (!deleting) return;
		const hashes = selection.hashes;
		try {
			const message = deletionFailures(await deleteImages(hashes));
			collectionsStore.refresh();
			if (!message) {
				deleting = null;
				ondone();
				return;
			}
			deletedSome = true;
			deleting = { copies: await copiesOf(hashes), message };
		} catch (e) {
			const message = e instanceof Error ? e.message : 'Delete failed';
			deleting = { copies: deleting?.copies ?? [], message };
		}
	}

	/** The files of this source the selected images hold, to move away. */
	async function askMove(to: Source) {
		picker = null;
		busy = true;
		error = null;
		try {
			const copies = (await copiesOf(selection.hashes)).filter((c) => c.source_id === sourceId);
			if (copies.length === 0) {
				error = 'The selected images have no files in this source.';
				return;
			}
			moving = { to, copies, message: '' };
		} catch (e) {
			error = e instanceof Error ? e.message : 'The files could not be read';
		} finally {
			busy = false;
		}
	}

	async function confirmMove() {
		if (!moving || sourceId === undefined) return;
		const { to, copies } = moving;
		busy = true;
		try {
			const result = await moveCopies(
				sourceId,
				to.id,
				copies.map((c) => c.relative_path)
			);
			collectionsStore.refresh();
			moving = null;
			error = moveFailures(result) || null;
			ondone();
		} catch (e) {
			const message = e instanceof Error ? e.message : 'The move failed';
			moving = { to, copies, message };
		} finally {
			busy = false;
		}
	}

	function cancelDelete() {
		deleting = null;
		if (deletedSome) ondone();
	}

	function onWindowKeydown(e: KeyboardEvent) {
		// The dialogs handle their own Escape.
		if (e.key !== 'Escape' || deleting || moving) return;
		if (picker) picker = null;
		else selection.stop();
	}
</script>

<svelte:window onkeydown={onWindowKeydown} />

<div class="bar" role="toolbar" aria-label="Selected images">
	{#if picker}
		<div class="picker">
			<!-- svelte-ignore a11y_autofocus -->
			<input
				class="control"
				placeholder={picker === 'move'
					? 'Source…'
					: picker === 'collection'
						? 'Collection…'
						: picker === 'tag'
							? 'Tag, or a new name…'
							: 'Tag to remove…'}
				bind:value={query}
				oninput={onQuery}
				onkeydown={onQueryKeydown}
				disabled={busy}
				autofocus
			/>
			<ul>
				{#if picker === 'move'}
					{#if fromSource && !fromSource.writable}
						<li class="empty">This source is read-only. Mark it writable in Settings to move its files.</li>
					{:else}
						{#each moveTargets as s (s.id)}
							<li><button disabled={busy} onclick={() => askMove(s)}>{sourceName(s)}</button></li>
						{:else}
							<li class="empty">No other writable source. Sources are marked writable in Settings.</li>
						{/each}
					{/if}
				{:else if picker === 'collection'}
					{#each targets as c (c.id)}
						<li><button disabled={busy} onclick={() => run((h) => addCollectionImages(c.id, h))}>{c.name}</button></li>
					{:else}
						<li class="empty">No collection of yours matches.</li>
					{/each}
				{:else}
					{#each tags as t (t.id)}
						<li><button disabled={busy} onclick={() => applyTag(t)}>{t.name}</button></li>
					{/each}
				{/if}
			</ul>
		</div>
	{/if}
	<span class="count">{selection.count} selected</span>
	<button class="control" disabled={none || busy} onclick={() => run((h) => archiveImages(h, !archived))}>
		{archived ? 'Unarchive' : 'Archive'}
	</button>
	<button
		class="control"
		disabled={selection.count < 2 || busy}
		title="Review the selected images one against another, flagging what to keep"
		onclick={() => goto(`/review?images=${selection.hashes.join(',')}`)}
	>
		Review
	</button>
	<button class="control" class:open={picker === 'tag'} disabled={none || busy} onclick={() => open('tag')}>Tag</button>
	<button class="control" class:open={picker === 'untag'} disabled={none || busy} onclick={() => open('untag')}>Untag</button>
	<button class="control" class:open={picker === 'collection'} disabled={none || busy} onclick={() => open('collection')}>
		Add to collection
	</button>
	{#if sourceId !== undefined}
		<button
			class="control"
			class:open={picker === 'move'}
			disabled={none || busy}
			title="Move the selected files out of this source, into another"
			onclick={openMove}
		>
			Move to source
		</button>
	{/if}
	{#if collectionId !== undefined}
		<button class="control" disabled={none || busy} onclick={() => run((h) => removeCollectionImages(collectionId, h))}>
			Remove from collection
		</button>
	{/if}
	<button class="control control-danger" disabled={none || busy} onclick={askDelete}>Delete from disk…</button>
	<button class="control control-primary" onclick={() => selection.stop()}>Done</button>
	{#if error}
		<p class="error">{error}</p>
	{/if}
</div>

{#if moving}
	<MoveDialog
		to={moving.to}
		copies={moving.copies}
		message={moving.message}
		{busy}
		onconfirm={confirmMove}
		oncancel={() => (moving = null)}
	/>
{/if}

{#if deleting}
	<DeleteDialog
		images={selection.count}
		copies={deleting.copies}
		message={deleting.message}
		onconfirm={confirmDelete}
		oncancel={cancelDelete}
	/>
{/if}

<style>
	.bar {
		position: fixed;
		left: 50%;
		bottom: 16px;
		transform: translateX(-50%);
		z-index: 40;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: center;
		gap: 8px;
		width: max-content;
		max-width: calc(100vw - 32px);
		box-sizing: border-box;
		padding: 8px 12px;
		background: #1a1a1a;
		border: 1px solid #444;
		border-radius: 8px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
	}

	.count {
		color: #ccc;
		font-size: 0.85rem;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.control.open {
		border-color: var(--control-focus);
	}

	.picker {
		position: absolute;
		bottom: calc(100% + 6px);
		left: 0;
		right: 0;
		padding: 8px;
		background: #1a1a1a;
		border: 1px solid #444;
		border-radius: 6px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
	}

	.picker input {
		width: 100%;
		box-sizing: border-box;
	}

	.picker ul {
		list-style: none;
		margin: 6px 0 0;
		padding: 0;
		max-height: 40vh;
		overflow-y: auto;
	}

	.picker li button {
		width: 100%;
		padding: 6px 8px;
		text-align: left;
		background: none;
		border: none;
		border-radius: 4px;
		color: #ccc;
		cursor: pointer;
	}

	.picker li button:hover:not(:disabled) {
		background: #2a2a2a;
		color: #fff;
	}

	.empty {
		padding: 6px 8px;
		color: #888;
		font-size: 0.85rem;
	}

	.error {
		flex-basis: 100%;
		margin: 0;
		color: #f66;
		font-size: 0.85rem;
		text-align: center;
	}
</style>
