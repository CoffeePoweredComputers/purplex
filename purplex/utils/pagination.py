"""
Custom pagination classes for Purplex.

Provides StandardPagination which extends DRF's PageNumberPagination
to include `total_pages` and `current_page` in every paginated response.
This matches the PaginatedResponse<T> interface expected by the frontend
useDataTable composable.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Pagination class that returns total_pages and current_page alongside
    the standard DRF fields (count, next, previous, results).

    Frontend expects:
        {
            results: T[],
            count: number,
            total_pages: number,
            current_page: number,
            next: string | null,
            previous: string | null,
        }

    The page_size_query_param is set to 'page_size' so the frontend can
    control how many items per page via ?page_size=25.
    """

    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "results": data,
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            }
        )

    def get_paginated_response_schema(self, schema):
        """OpenAPI schema for the paginated response."""
        return {
            "type": "object",
            "required": [
                "results",
                "count",
                "total_pages",
                "current_page",
            ],
            "properties": {
                "results": schema,
                "count": {
                    "type": "integer",
                    "example": 42,
                },
                "total_pages": {
                    "type": "integer",
                    "example": 2,
                },
                "current_page": {
                    "type": "integer",
                    "example": 1,
                },
                "next": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                },
                "previous": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                },
            },
        }
