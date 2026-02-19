/**
 * clientSidePaginate - Adapts a flat array into a PaginatedResponseWithFilters shape.
 *
 * Four of five admin pages use APIs that return flat arrays (ProblemSet[], Course[], etc.).
 * useDataTable expects PaginatedResponseWithFilters<T, F>. This utility bridges the gap
 * by slicing the array into pages and optionally applying client-side search.
 *
 * Usage:
 *   const fetchFn = async (params) => {
 *     const allItems = await api.getItems();
 *     return clientSidePaginate(allItems, params, {
 *       searchFn: (item, q) => item.title.toLowerCase().includes(q.toLowerCase()),
 *     });
 *   };
 */
import type { PaginatedResponseWithFilters } from '@/types/datatable';

export interface ClientSidePaginateOptions<T, F = Record<string, unknown>> {
  /** Custom search function. If provided and params.search is set, filters items first. */
  searchFn?: (item: T, query: string) => boolean;
  /** Static filter metadata to include in the response. */
  filters?: F;
}

export function clientSidePaginate<T, F = Record<string, unknown>>(
  allItems: T[],
  params: { page: number; page_size: number; search?: string },
  options?: ClientSidePaginateOptions<T, F>
): PaginatedResponseWithFilters<T, F> {
  let filtered = allItems;

  // Apply client-side search if a search function and query are provided
  if (options?.searchFn && params.search?.trim()) {
    const query = params.search.trim();
    filtered = allItems.filter(item => options.searchFn!(item, query));
  }

  const count = filtered.length;
  const pageSize = params.page_size;
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const currentPage = Math.min(Math.max(1, params.page), totalPages);

  const start = (currentPage - 1) * pageSize;
  const end = Math.min(start + pageSize, count);
  const results = filtered.slice(start, end);

  return {
    results,
    count,
    total_pages: totalPages,
    current_page: currentPage,
    next: currentPage < totalPages ? String(currentPage + 1) : null,
    previous: currentPage > 1 ? String(currentPage - 1) : null,
    filters: options?.filters,
  };
}
