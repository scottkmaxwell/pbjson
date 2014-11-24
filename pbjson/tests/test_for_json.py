from unittest import TestCase, main
import pbjson


class ForJson(object):
    # noinspection PyMethodMayBeStatic
    def for_json(self):
        return {'for_json': 1}


class NestedForJson(object):
    # noinspection PyMethodMayBeStatic
    def for_json(self):
        return {'nested': ForJson()}


class ForJsonList(object):
    # noinspection PyMethodMayBeStatic
    def for_json(self):
        return ['list']


class DictForJson(dict):
    # noinspection PyMethodMayBeStatic
    def for_json(self):
        return {'alpha': 1}


class ListForJson(list):
    # noinspection PyMethodMayBeStatic
    def for_json(self):
        return ['list']


class TestForJson(TestCase):
    def assertRoundTrip(self, obj, other, use_for_json=True):
        if use_for_json is None:
            # None will use the default
            s = pbjson.dumps(obj)
        else:
            s = pbjson.dumps(obj, use_for_json=use_for_json)
        self.assertEqual(
            pbjson.loads(s),
            other)

    def test_for_json_encodes_stand_alone_object(self):
        self.assertRoundTrip(
            ForJson(),
            ForJson().for_json())

    def test_for_json_encodes_object_nested_in_dict(self):
        self.assertRoundTrip(
            {'hooray': ForJson()},
            {'hooray': ForJson().for_json()})

    def test_for_json_encodes_object_nested_in_list_within_dict(self):
        self.assertRoundTrip(
            {'list': [0, ForJson(), 2, 3]},
            {'list': [0, ForJson().for_json(), 2, 3]})

    def test_for_json_encodes_object_nested_within_object(self):
        self.assertRoundTrip(
            NestedForJson(),
            {'nested': {'for_json': 1}})

    def test_for_json_encodes_list(self):
        self.assertRoundTrip(
            ForJsonList(),
            ForJsonList().for_json())

    def test_for_json_encodes_list_within_object(self):
        self.assertRoundTrip(
            {'nested': ForJsonList()},
            {'nested': ForJsonList().for_json()})

    def test_for_json_encodes_dict_subclass(self):
        self.assertRoundTrip(
            DictForJson(a=1),
            DictForJson(a=1).for_json())

    def test_for_json_encodes_list_subclass(self):
        self.assertRoundTrip(
            ListForJson(['l']),
            ListForJson(['l']).for_json())

    def test_for_json_ignored_if_not_true_with_dict_subclass(self):
        for use_for_json in (None, False):
            self.assertRoundTrip(
                DictForJson(a=1),
                {'a': 1},
                use_for_json=use_for_json)

    def test_for_json_ignored_if_not_true_with_list_subclass(self):
        for use_for_json in (None, False):
            self.assertRoundTrip(
                ListForJson(['l']),
                ['l'],
                use_for_json=use_for_json)

    def test_raises_typeerror_if_for_json_not_true_with_object(self):
        self.assertRaises(TypeError, pbjson.dumps, ForJson())
        self.assertRaises(TypeError, pbjson.dumps, ForJson(), use_for_json=False)

if __name__ == '__main__':
    main()
