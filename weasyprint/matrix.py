"""Transformation matrix."""


class Matrix(list):
    def __init__(self, a=1, b=0, c=0, d=1, e=0, f=0, matrix=None):
        if matrix is None:
            matrix = [[a, b, 0], [c, d, 0], [e, f, 1]]
        super().__init__(matrix)

    def __matmul__(self, other):
        assert len(self[0]) == len(other) == len(other[0]) == 3
        return Matrix(matrix=[
            [sum(self[i][k] * other[k][j] for k in range(3)) for j in range(3)]
            for i in range(len(self))])

    @property
    def invert(self):
        d = self.determinant
        return Matrix(matrix=[
            [
                (self[1][1] * self[2][2] - self[1][2] * self[2][1]) / d,
                (self[0][1] * self[2][2] - self[0][2] * self[2][1]) / -d,
                (self[0][1] * self[1][2] - self[0][2] * self[1][1]) / d,
            ],
            [
                (self[1][0] * self[2][2] - self[1][2] * self[2][0]) / -d,
                (self[0][0] * self[2][2] - self[0][2] * self[2][0]) / d,
                (self[0][0] * self[1][2] - self[0][2] * self[1][0]) / -d,
            ],
            [
                (self[1][0] * self[2][1] - self[1][1] * self[2][0]) / d,
                (self[0][0] * self[2][1] - self[0][1] * self[2][0]) / -d,
                (self[0][0] * self[1][1] - self[0][1] * self[1][0]) / d,
            ],
        ])

    @property
    def determinant(self):
        assert len(self) == len(self[0]) == 3
        return (
            self[0][0] * (self[1][1] * self[2][2] - self[1][2] * self[2][1]) -
            self[1][0] * (self[0][1] * self[2][2] - self[0][2] * self[2][1]) +
            self[2][0] * (self[0][1] * self[1][2] - self[0][2] * self[1][1]))

    def transform_point(self, x, y):
        return (Matrix(matrix=[[x, y, 1]]) @ self)[0][:2]

    @property
    def values(self):
        (a, b), (c, d), (e, f) = [column[:2] for column in self]
        return a, b, c, d, e, f
