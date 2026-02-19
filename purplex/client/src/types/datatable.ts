/**
 * DataTable type definitions for the standardized table component system.
 *
 * These types support the generic useDataTable composable and DataTable component,
 * providing a consistent interface for paginated tables across the admin panel.
 */

// ===== PAGINATION TYPES =====

/**
 * Standard paginated API response format.
 * Matches Django REST Framework pagination output.
 */
export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  total_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
}

/**
 * Extended paginated response with filter metadata.
 * Used when the API returns available filter options.
 */
export interface PaginatedResponseWithFilters<T, F = Record<string, unknown>>
  extends PaginatedResponse<T> {
  filters?: F;
}

// ===== COLUMN DEFINITION TYPES =====

/**
 * Column definition for DataTable component.
 * Defines how each column is rendered and behaves.
 */
export interface DataTableColumn<T = unknown> {
  /** Property key in the data object (supports dot notation for nested: 'user.email') */
  key: string;
  /** Column header display text */
  label: string;
  /** Text alignment within the cell */
  align?: 'left' | 'center' | 'right';
  /** CSS width value (e.g., '100px', '20%') */
  width?: string;
  /** Hide this column on mobile viewports */
  hideOnMobile?: boolean;
  /** Named slot for custom cell rendering (e.g., 'cell-role') */
  slot?: string;
  /** Custom render function for cell content */
  render?: (value: unknown, row: T) => string;
  /** Enable sorting on this column (future enhancement) */
  sortable?: boolean;
}

// ===== FILTER TYPES =====

/**
 * Filter definition for DataTable filtering.
 */
export interface DataTableFilter {
  /** Filter parameter key sent to API */
  key: string;
  /** Display label for the filter */
  label: string;
  /** Filter input type */
  type: 'select' | 'search';
  /** Options for select filters */
  options?: Array<{ value: string; label: string }>;
  /** Placeholder text for input */
  placeholder?: string;
}

/**
 * Active filter state with display information.
 */
export interface ActiveFilter {
  key: string;
  value: string;
  label: string;
  displayValue: string;
}

// ===== COMPOSABLE TYPES =====

/**
 * Query parameters sent to the paginated API endpoint.
 */
export interface DataTableQueryParams {
  page: number;
  page_size: number;
  search?: string;
  [key: string]: string | number | undefined;
}

/**
 * Options for the useDataTable composable.
 */
export interface UseDataTableOptions<T, F = Record<string, unknown>> {
  /** Function to fetch paginated data */
  fetchFn: (params: DataTableQueryParams) => Promise<PaginatedResponseWithFilters<T, F>>;
  /** Initial page size (default: 25) */
  initialPageSize?: number;
  /** Debounce delay for search in ms (default: 300) */
  debounceMs?: number;
  /** Filter keys to track (for clearing) */
  filterKeys?: string[];
}

// ===== BADGE TYPES =====

/** Badge variant for StatusBadge component */
export type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'default' | 'admin' | 'instructor';

/**
 * Badge configuration for mapping values to variants.
 */
export interface BadgeConfig {
  value: string;
  variant: BadgeVariant;
  label?: string;
}
