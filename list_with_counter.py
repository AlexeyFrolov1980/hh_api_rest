import operator

class list_with_counter:

    def __init__(self):
        self.list_items = {}

    def add_item(self, item, value=1):

        if item is None: return

        if item == '': return

        if value is not None:
            if self.list_items.get(item) is not None:
                self.list_items[item] += value
            else:
                self.list_items[item] = value


    def add_items(self, items):

        for i in items:
            self.add_item(i)

    def __str__(self):
        res = ''
        for key, value in self.list_items.items():
            res += str(key) + ': ' + str(value) + '\n'

        return res

    def sort_by_value(self, reverse=True):
        sorted_items = sorted(self.list_items.items(), key=lambda x: x[1], reverse=reverse)
        self.list_items = dict(sorted_items)

    def calc_percentage(self):
        total_sum = sum(self.list_items.values())

        res = list_with_counter()

        for key, value in self.list_items.items():
           res.list_items[key] = value/total_sum*100

        return res

    def __getitem__(self, key):
        return self.list_items[key]



