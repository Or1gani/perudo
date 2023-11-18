class Game:
    def __init__(self):
        self.a = []
    def func(self, id):
        self.a.append(id)
g = Game()
g1 = Game()
g.func(123)
g1.func(0)

print(g.a)
print(g1.a)