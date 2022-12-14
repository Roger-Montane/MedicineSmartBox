import numpy as np
import pandas as pd


class DataCreator:
    def __init__(self, n_codes: int = 500, code_types=None):
        if code_types is None:
            code_types = ['gtin-13']

        self.n = n_codes
        self.types = code_types

    @staticmethod
    def _generate_random_numbers(n: int):
        return np.random.randint(1, 11, size=n)

    def _create_gtin13_code(self):
        prefix = int(''.join(map(str, self._generate_random_numbers(n=2))))
        manufacturer = int(''.join(map(str, self._generate_random_numbers(n=5))))
        product = int(''.join(map(str, self._generate_random_numbers(n=5))))
        control = int(''.join(map(str, self._generate_random_numbers(n=1))))

        return int(str(prefix) + str(manufacturer) + str(product) + str(control))

    def run(self):
        codes = []
        for _ in range(self.n):
            c = self._create_gtin13_code()
            if c not in codes:
                codes.append(c)
        return codes


if __name__ == "__main__":
    dc = DataCreator(n_codes=20)
    print(dc.run())
