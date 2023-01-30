from unittest import IsolatedAsyncioTestCase


class TestFilterData(IsolatedAsyncioTestCase):
    def setUp(self):
        self.data = [
            {"id": 1, "name": "John", "age": 30, "city": "New York"},
            {"id": 2, "name": "Jane", "age": 25, "city": "San Francisco"},
            {"id": 3, "name": "Bob", "age": 35, "city": "New York"},
            {"id": 4, "name": "Alice", "age": 28, "city": "San Francisco"},
            {"id": 5, "name": "Charlie", "age": 32, "city": "Los Angeles"},
        ]

        self.base_filter = {
            "pagination": {"currentPageIndex": 1, "pageSize": 30},
            "sorting": {
                "sortingColumn": {
                    "id": "id",
                    "sortingField": "name",
                    "header": "Name",
                    "minWidth": 180,
                },
                "sortingDescending": False,
            },
            "filtering": None,
        }

    async def test_and_operation(self):
        from common.lib.filter import filter_data

        filter = {
            "tokens": [
                {"propertyKey": "city", "operator": "=", "value": "New York"},
                {"propertyKey": "age", "operator": ">", "value": 30},
            ],
            "operation": "and",
        }
        expected_output = [{"id": 3, "name": "Bob", "age": 35, "city": "New York"}]
        res = await filter_data(self.data, {**self.base_filter, "filtering": filter})
        self.assertEqual(
            res.data,
            expected_output,
        )

    async def test_or_operation(self):
        from common.lib.filter import filter_data

        filter = {
            "tokens": [
                {"propertyKey": "city", "operator": "=", "value": "New York"},
                {"propertyKey": "age", "operator": ">", "value": 30},
            ],
            "operation": "or",
        }
        expected_output = [
            {"id": 1, "name": "John", "age": 30, "city": "New York"},
            {"id": 3, "name": "Bob", "age": 35, "city": "New York"},
            {"id": 5, "name": "Charlie", "age": 32, "city": "Los Angeles"},
        ]

        expected_output = sorted(expected_output, key=lambda x: x["name"])
        res = await filter_data(self.data, {**self.base_filter, "filtering": filter})
        self.assertEqual(
            res.data,
            expected_output,
        )

    async def test_empty_filter(self):
        from common.lib.filter import filter_data

        expected_output = sorted(self.data, key=lambda x: x["name"])
        filter = {}
        res = await filter_data(self.data, {**self.base_filter, "filtering": filter})
        self.assertEqual(
            res.data,
            expected_output,
        )

    async def test_filter_no_tokens(self):
        from common.lib.filter import filter_data

        filter = {"operation": "and"}
        expected_output = sorted(self.data, key=lambda x: x["name"])
        res = await filter_data(self.data, {**self.base_filter, "filtering": filter})
        self.assertEqual(
            res.data,
            expected_output,
        )

    async def test_filter_no_matching_data(self):
        from common.lib.filter import filter_data

        filter = {
            "tokens": [{"propertyKey": "city", "operator": "=", "value": "Irvine"}]
        }
        expected_output = []
        res = await filter_data(self.data, {**self.base_filter, "filtering": filter})
        self.assertEqual(
            res.data,
            expected_output,
        )

    async def test_filter_with_invalid_operator(self):
        from common.lib.filter import filter_data

        filter = {
            "tokens": [{"propertyKey": "age", "operator": "invalid", "value": 30}]
        }
        with self.assertRaises(ValueError):
            await filter_data(self.data, {**self.base_filter, "filtering": filter})

    async def test_filter_with_invalid_property_key(self):
        from common.lib.filter import filter_data

        filter = {
            "tokens": [{"propertyKey": "invalid", "operator": "=", "value": "New York"}]
        }
        with self.assertRaises(KeyError):
            res = await filter_data(
                self.data, {**self.base_filter, "filtering": filter}
            )
            print(res)
