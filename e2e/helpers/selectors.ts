/**
 * Centralized selectors for E2E tests.
 *
 * Sources: actual Vue component templates (no data-testid attributes exist
 * in the codebase). Prefer aria/role selectors where available, then CSS
 * class selectors.
 *
 * When the DOM structure changes, update this file rather than patching
 * individual test files.
 */

// ---------------------------------------------------------------------------
// Navigation (NavBar.vue)
// ---------------------------------------------------------------------------
export const nav = {
  /** Sticky navbar wrapper */
  wrapper: '.navbar-wrapper',
  /** Logo link (navigates to /home) */
  logoLink: '.logo-link',
  /** Brand text next to logo */
  logoText: '.logo-text',
  /** Instructor dashboard link (visible when role is instructor) */
  instructorLink: '.instructor-item',
  /** Admin dashboard link (visible when role is admin) */
  adminLink: '.admin-item',
  /** Account button (opens AccountModal) */
  accountButton: '.account-item',
} as const;

// ---------------------------------------------------------------------------
// DataTable (DataTable.vue + DataTablePagination.vue)
// ---------------------------------------------------------------------------
export const dataTable = {
  /** Top-level container */
  container: '.data-table-container',
  /** The <table> element */
  table: '.data-table',
  /** All body rows */
  rows: '.data-table tbody tr',
  /** Column headers */
  headers: '.data-table th',
  /** Results summary text (e.g. "Showing 1-10 of 42") */
  resultsCount: '.results-count',
  /** Pagination nav wrapper */
  pagination: 'nav.pagination',
  /** Any pagination button */
  paginationButton: '.pagination-btn',
  /** Numbered page buttons */
  pageNumber: '.pagination-btn.page-number',
  /** Active page button */
  pageNumberActive: '.pagination-btn.page-number.active',
  /** Page size <select> */
  pageSizeSelect: '#page-size',
  /** Loading state (AsyncLoader) */
  loading: '.loading-container',
  /** Error state */
  error: '.error-state',
  /** Retry button inside error state */
  retryButton: '.retry-button',
  /** Empty state */
  empty: '.empty-state',
} as const;

// ---------------------------------------------------------------------------
// Forms (Login.vue and general patterns)
// ---------------------------------------------------------------------------
export const forms = {
  /** Login form container */
  loginForm: '#login-form',
  /** Email input on login page */
  emailInput: '#email',
  /** Password input on login page */
  passwordInput: '#psw',
  /** Login submit button (first button in .login-btns) */
  loginButton: '.login-btns button:first-child',
  /** Create account button (second button in .login-btns) */
  createAccountButton: '.login-btns button:nth-child(2)',
  /** Google login button (third button in .login-btns) */
  googleButton: '.login-btns button:nth-child(3)',
  /** Error message banner */
  errorMessage: '.error-message',
  /** Info message banner */
  infoMessage: '.info-message',
} as const;

// ---------------------------------------------------------------------------
// Modals
// ---------------------------------------------------------------------------
export const modals = {
  /** Generic modal overlay (all modals use .modal-overlay) */
  overlay: '.modal-overlay',
  /** Generic modal content panel */
  content: '.modal-content',

  // AccountModal
  /** Account modal (identified by aria-labelledby) */
  account: '[aria-labelledby="account-modal-title"]',
  /** Close button inside account modal */
  accountClose: '[aria-labelledby="account-modal-title"] .close-button',
  /** User display name in account modal */
  accountUserName: '.user-name',
  /** User email in account modal */
  accountUserEmail: '.user-email',
  /** Role badge in account modal */
  accountRoleBadge: '.role-badge',

  // CourseEnrollmentModal
  /** Enrollment modal (identified by aria-labelledby) */
  enrollment: '[aria-labelledby="enrollment-modal-title"]',
  /** Course ID input in enrollment modal */
  enrollmentCourseInput: '#course-id',
  /** Lookup button in enrollment modal */
  enrollmentLookupButton: '.lookup-btn',
  /** Course preview card after lookup */
  enrollmentCoursePreview: '.course-preview',
  /** Close button in enrollment modal */
  enrollmentClose: '[aria-labelledby="enrollment-modal-title"] .close-btn',

  // ViewSubmissionModal
  /** Submission modal (identified by aria-labelledby) */
  submission: '[aria-labelledby="submission-modal-title"]',
  /** Close button in submission modal */
  submissionClose: '[aria-labelledby="submission-modal-title"] .close-btn',

  // ConfirmDialog
  /** Confirm dialog (uses role="alertdialog") */
  confirmDialog: '[role="alertdialog"]',
  /** Cancel button in confirm dialog */
  confirmCancel: '[role="alertdialog"] .btn-secondary',
  /** Danger confirm button */
  confirmDanger: '[role="alertdialog"] .btn-danger',
  /** Warning confirm button */
  confirmWarning: '[role="alertdialog"] .btn-warning',
} as const;

// ---------------------------------------------------------------------------
// Problem Set (ProblemSet.vue)
// ---------------------------------------------------------------------------
export const problemSet = {
  /** Top-level problem set container */
  container: '.problem-set-container',
  /** Individual problem progress buttons in the nav bar */
  problemButtons: '.progress-bar',
  /** Currently active problem button */
  activeProblem: '.progress-bar.active',
  /** Completed problem indicator */
  completedProblem: '.progress-bar.completed',
  /** In-progress problem indicator */
  inProgressProblem: '.progress-bar.in_progress',
  /** Not-started problem indicator */
  notStartedProblem: '.progress-bar.not_started',
  /** Previous problem navigation button */
  prevButton: '.nav-button:first-child',
  /** Next problem navigation button */
  nextButton: '.nav-button:last-child',
  /** Progress summary (completed/in-progress/remaining counts) */
  progressSummary: '.progress-summary',
  /** Deadline banner (role="alert") */
  deadlineBanner: '.deadline-banner',
  /** Locked deadline state */
  deadlineLocked: '.deadline-banner.deadline-locked',
  /** Code editor section */
  editorSection: '#code-editor',
  /** Submission section (contains InputSelector) */
  submissionSection: '.submission-section',
  /** Submit button (inside DescriptionInput / activity inputs) */
  submitButton: '#submitButton',
  /** Submit button by class (alternative selector) */
  submitButtonByClass: '.submit-button',
  /** Prompt editor wrapper */
  promptEditor: '#promptEditor',
  /** Workspace area */
  workspace: '#main-workspace',
} as const;

// ---------------------------------------------------------------------------
// Home (Home.vue)
// ---------------------------------------------------------------------------
export const home = {
  /** Top-level home container */
  container: '.home-container',
  /** Problem set cards in the gallery grid */
  problemSetCard: '.problem-set-card',
  /** Course section */
  courseSection: '.course-section',
  /** Course title heading */
  courseTitle: '.course-title',
  /** Progress bar fill (inside problem set cards) */
  progressBarFill: '.progress-bar-fill',
  /** Progress text ("3/5 completed") */
  progressText: '.progress-text',
  /** Join course button (floating or inline) */
  joinCourseButton: '.add-course-btn',
  /** Empty state when no courses enrolled */
  emptyState: '.empty-state-container',
  /** Gallery grid of problem set cards */
  galleryGrid: '.gallery-grid',
  /** Skeleton loading card */
  skeletonCard: '.problem-set-card.skeleton',
} as const;

// ---------------------------------------------------------------------------
// Feedback (Feedback.vue)
// ---------------------------------------------------------------------------
export const feedback = {
  /** Top-level feedback container */
  container: '.feedback-container',
  /** Feedback header with title + attempt selector */
  header: '.feedback-header',
  /** Score badge showing percentage */
  scoreBadge: '.attempt-score-badge',
  /** Attempt selector dropdown trigger */
  attemptSelector: '.attempt-dropdown-trigger',
  /** Metric cards (correctness and abstraction) */
  metricCard: '.metric-card',
  /** Correctness progress bar */
  correctnessBar: '.progress-bar-fill',
  /** Generating feedback loading panel */
  generatingPanel: '.generating-feedback-panel',
  /** Navigation skeleton (during problem switch) */
  navigationSkeleton: '.navigation-skeleton-panel',
} as const;

// ---------------------------------------------------------------------------
// Common / Shared
// ---------------------------------------------------------------------------
export const common = {
  /** Loading spinner (AsyncLoader.vue) */
  spinner: '.async-loader',
  /** Spinner animation element */
  spinnerIcon: '.spinner',
  /** Skeleton loading elements (generic) */
  skeleton: '.skeleton',
  /** Empty state (generic, used in Home and DataTable) */
  emptyState: '.empty-state',
  /** Error state (generic, used in DataTable) */
  errorState: '.error-state',
  /** Loading container (used in DataTable and ProblemSet) */
  loadingContainer: '.loading-container',
  /** Dialog overlay (ConfirmDialog uses .dialog-overlay) */
  dialogOverlay: '.dialog-overlay',
} as const;
