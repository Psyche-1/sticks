import sys
import random
import pygame


# Размеры окна и графики
CELL_SIZE = 60
PADDING = 50

# Цвета (RGB)
COLOR_BG = (30, 30, 30)
COLOR_GRID = (60, 60, 60)
COLOR_BORDER = (200, 200, 200)
COLOR_POSSIBLE = (100, 100, 100)  # Светло-серый для доступных ходов
COLOR_P1 = (50, 150, 255)         # Синий
COLOR_P2 = (255, 50, 50)          # Красный
COLOR_P3 = (50, 200, 50)          # Зеленый
COLOR_P4 = (255, 230, 0)          # Ярко-желтый
COLOR_TEXT = (255, 255, 255)

class Game:
    def __init__(self, grid_size, player_types):
        pygame.init()
        
        # Задаем глобальные переменные на основе выбора пользователя
        global GRID_SIZE, WIDTH, HEIGHT
        GRID_SIZE = grid_size
        WIDTH = GRID_SIZE * CELL_SIZE + PADDING * 2 + 30
        HEIGHT = GRID_SIZE * CELL_SIZE + PADDING * 2 + 30
        
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sticks")
        
        # Список типов игроков: 1 - Синий (всегда человек), остальные по выбору ("human" или "bot")
        # Индексы в коде: 0 - P1, 1 - P2, 2 - P3, 3 - P4
        self.player_types = player_types
        self.num_players = len(player_types)
        
        # Начальные позиции для всех возможных 4 игроков
        self.positions = [
            (0, GRID_SIZE),      # P1: Левый нижний
            (GRID_SIZE, 0),      # P2: Правый верхний
            (GRID_SIZE, GRID_SIZE), # P3: Правый нижний
            (0, 0)               # P4: Левый верхний
        ][:self.num_players]
        
        self.player_colors = [COLOR_P1, COLOR_P2, COLOR_P3, COLOR_P4][:self.num_players]
        self.player_names = ["Blue (P1)", "Red (P2)", "Green (P3)", "Yellow (P4)"][:self.num_players]
        
        # Статусы игроков: True - играет, False - застрял (выбыл)
        self.active_players = [True] * self.num_players
        
        self.current_idx = 0  # Индекс текущего игрока (0 до num_players-1)
        self.game_over = False
        self.winner = None

        # Хранилище заблокированных отрезков. 
        # Формат: захешированная пара точек ((x1, y1), (x2, y2)), где x1<=x2
        self.used_edges = {}
        
        # Инициализируем жирные края поля как заблокированные пути
        self._init_borders()
        
        # Храним последний сделанный отрезок для каждого игрока для прорисовки шлейфа.
        # Формат: [None, None, None, None] (по одному объекту ((x1,y1), (x2,y2)) на игрока)
        self.last_edges = [None] * self.num_players
        
        # Счетчик побед для каждого игрока (изначально у всех 0)
        self.scores = [0] * self.num_players
        
        self._score_counted = False
    
    def reset_game(self):
        """Полный сброс игры с сохранением текущих настроек поля и игроков"""
        self.positions = [
            (0, GRID_SIZE),         # P1
            (GRID_SIZE, 0),         # P2
            (GRID_SIZE, GRID_SIZE), # P3
            (0, 0)                  # P4
        ][:self.num_players]
        
        self.active_players = [True] * self.num_players
        self.current_idx = 0
        self.game_over = False
        self.winner = None
        self.used_edges = {}
        self._init_borders()
        self.last_edges = [None] * self.num_players
        self._score_counted = False


    def _init_borders(self):
        for i in range(GRID_SIZE):
            # Горизонтальные края (верх и низ)
            self.used_edges[self._get_norm_edge((i, 0), (i + 1, 0))] = COLOR_BORDER
            self.used_edges[self._get_norm_edge((i, GRID_SIZE), (i + 1, GRID_SIZE))] = COLOR_BORDER
            # Вертикальные края (лево и право)
            self.used_edges[self._get_norm_edge((0, i), (0, i + 1))] = COLOR_BORDER
            self.used_edges[self._get_norm_edge((GRID_SIZE, i), (GRID_SIZE, i + 1))] = COLOR_BORDER

    def _get_norm_edge(self, p1, p2):
        """Возвращает отрезок в стандартном порядке, чтобы избежать дублирования направления"""
        return (p1, p2) if p1 <= p2 else (p2, p1)

    def get_current_pos(self):
        return self.positions[self.current_idx]

    def get_possible_moves(self, player_idx=None):
        """Ищет все свободные отрезки вокруг текущего игрока во всех 8 направлениях"""
        idx = self.current_idx if player_idx is None else player_idx
        cx, cy = self.positions[idx]
        moves = []
        
        # Все 8 направлений: С, Ю, З, В, СЗ, СВ, ЮЗ, ЮВ
        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1)
        ]
        
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            # Проверяем, что точка внутри поля
            if 0 <= nx <= GRID_SIZE and 0 <= ny <= GRID_SIZE:
                edge = self._get_norm_edge((cx, cy), (nx, ny))
                if edge not in self.used_edges:
                    moves.append((nx, ny))
        return moves

    def _next_turn(self):
        """Передает ход следующему АКТИВНОМУ игроку"""
        if self.game_over:
            return

        # Проверяем, сколько игроков еще в игре
        if self.active_players.count(True) <= 1:
            self.game_over = True
            # Победитель — единственный выживший, либо последний оставшийся
            if self.active_players.count(True) == 1:
                win_idx = self.active_players.index(True)
                self.winner = self.player_names[win_idx]
            else:
                self.winner = "Draw (Everyone Stuck)"
            return

        # Ищем следующего живого игрока по кругу
        while True:
            self.current_idx = (self.current_idx + 1) % self.num_players
            if self.active_players[self.current_idx]:
                break

    def to_screen_coords(self, grid_pos):
        """Перевод координат сетки в пиксели экрана"""
        x, y = grid_pos
        return PADDING + x * CELL_SIZE, PADDING + 30 + y * CELL_SIZE

    def make_move(self, next_pos):
        """Совершает ход текущего игрока, проверяет выбывание и начисляет очки победителю"""
        curr_pos = self.get_current_pos()
        edge = self._get_norm_edge(curr_pos, next_pos)
        
        # 1. Закрашиваем пройденную линию в цвет текущего игрока
        self.used_edges[edge] = self.player_colors[self.current_idx]
        
        # 2. Сохраняем направление хода для прорисовки неонового шлейфа (откуда -> куда)
        self.last_edges[self.current_idx] = (curr_pos, next_pos)
        
        # 3. Перемещаем фишку игрока в новую точку
        self.positions[self.current_idx] = next_pos
        
        # 4. Проверяем текущего игрока: не запер ли он сам себя своим же ходом?
        if not self.get_possible_moves(self.current_idx):
            self.active_players[self.current_idx] = False

        # 5. Передаем ход дальше следующему активному игроку
        self._next_turn()
        
        # 6. Проверяем нового текущего игрока. Если у него на начало его хода нет вариантов, 
        # он выбывает, а ход идет дальше по кругу, пока не найдем живого или игра не закончится.
        while not self.game_over and not self.get_possible_moves(self.current_idx):
            self.active_players[self.current_idx] = False
            self._next_turn()

        # 7. НАЧИСЛЕНИЕ ОЧКОВ ПРИ ОКОНЧАНИИ ИГРЫ
        # Если игра завершилась и определился единственный победитель
        if self.game_over and self.winner and self.winner != "Ничья (Все застряли)":
            # Защита: начисляем очко только один раз за партию
            if not self._score_counted:
                # Находим индекс выжившего игрока в списке по его имени
                try:
                    win_idx = self.player_names.index(self.winner)
                    self.scores[win_idx] += 1
                except ValueError:
                    pass
                self._score_counted = True


    def handle_click(self, mouse_pos):
        # Проверяем клик по кнопке рестарта в первую очередь
        if hasattr(self, 'restart_btn_rect') and self.restart_btn_rect.collidepoint(mouse_pos):
            self.reset_game()
            return
        
        # Если текущий игрок является ботом любого типа — клик игнорируется
        if self.game_over or "bot" in self.player_types[self.current_idx]:
            return

        possible_moves = self.get_possible_moves()
        curr_screen_pos = self.to_screen_coords(self.get_current_pos())
        
        for move in possible_moves:
            move_screen_pos = self.to_screen_coords(move)
            
            # Считаем расстояние от клика до середины отрезка для точного попадания
            mid_x = (curr_screen_pos[0] + move_screen_pos[0]) / 2
            mid_y = (curr_screen_pos[1] + move_screen_pos[1]) / 2
            
            distance = ((mouse_pos[0] - mid_x) ** 2 + (mouse_pos[1] - mid_y) ** 2) ** 0.5
            # Если кликнули близко к линии (в пределах 15 пикселей) — делаем ход
            if distance < 15:
                self.make_move(move)
                break

    def bot_turn(self):
        pygame.time.wait(1000)
        possible_moves = self.get_possible_moves()
        if not possible_moves:
            return

        bot_type = self.player_types[self.current_idx]

        if bot_type == "random_bot":
            # Старый добрый случайный ход
            self.make_move(random.choice(possible_moves))
            
        elif bot_type == "smart_bot":
            # Умный бот: ищет ход, который оставит ему наибольшее количество вариантов на будущее
            best_move = possible_moves[0]
            max_future_moves = -1
            
            # Временно симулируем ходы, чтобы посмотреть последствия
            for move in possible_moves:
                edge = self._get_norm_edge(self.get_current_pos(), move)
                
                # Гипотетически занимаем линию
                self.used_edges[edge] = self.player_colors[self.current_idx]
                # Запоминаем старую позицию и временно двигаем бота
                old_pos = self.positions[self.current_idx]
                self.positions[self.current_idx] = move
                
                # Считаем, сколько ходов у нас останется ИЗ ЭТОЙ НОВОЙ ТОЧКИ
                future_moves_count = len(self.get_possible_moves(self.current_idx))
                
                # Возвращаем всё назад
                self.positions[self.current_idx] = old_pos
                del self.used_edges[edge]
                
                # Нам нужен ход, который оставляет максимум выходов из ловушки
                if future_moves_count > max_future_moves:
                    max_future_moves = future_moves_count
                    best_move = move
                elif future_moves_count == max_future_moves:
                    # При равенстве вариантов выбираем ход ближе к центру поля, 
                    # чтобы не прижиматься к краям раньше времени
                    center = GRID_SIZE / 2
                    dist_best = ((best_move[0] - center)**2 + (best_move[1] - center)**2)
                    dist_curr = ((move[0] - center)**2 + (move[1] - center)**2)
                    if dist_curr < dist_best:
                        best_move = move
                        
            self.make_move(best_move)


    def draw(self):
        self.screen.fill(COLOR_BG)
        
        # 1. Рисуем базовую сетку (точки)
        for x in range(GRID_SIZE + 1):
            for y in range(GRID_SIZE + 1):
                pygame.draw.circle(self.screen, COLOR_GRID, self.to_screen_coords((x, y)), 3)

        # 2. Рисуем все занятые линии их собственными цветами
        for edge, color in self.used_edges.items():
            # РАСПАКОВЫВАЕМ ОТРЕЗОК НА ДВЕ ТОЧКИ:
            p1, p2 = edge
            p1_screen = self.to_screen_coords(p1)
            p2_screen = self.to_screen_coords(p2)
            pygame.draw.line(self.screen, color, p1_screen, p2_screen, 4)
            
        # 2.5. Рисуем визуальный шлейф и стрелочки направления движения
        for i in range(self.num_players):
            # Рисуем шлейф только если игрок уже сделал хотя бы один ход и он еще активен
            if self.last_edges[i] and self.active_players[i]:
                p1, p2 = self.last_edges[i]
                p1_scr = self.to_screen_coords(p1)
                p2_scr = self.to_screen_coords(p2)
                
                # Рисуем поверх существующей линии более жирную (толщина 7px) 
                # с небольшим осветлением/эффектом свечения (поднимаем яркость цвета игрока)
                r, g, b = self.player_colors[i]
                glow_color = (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255))
                pygame.draw.line(self.screen, glow_color, p1_scr, p2_scr, 7)
                
                # Вычисляем середину отрезка для отрисовки стрелочки направления
                mx = (p1_scr[0] + p2_scr[0]) / 2
                my = (p1_scr[1] + p2_scr[1]) / 2
                
                # Считаем вектор направления хода
                vx = p2_scr[0] - p1_scr[0]
                vy = p2_scr[1] - p1_scr[1]
                length = (vx**2 + vy**2)**0.5
                
                if length > 0:
                    # Нормализуем вектор направления движения
                    dx = vx / length
                    dy = vy / length
                    # Перпендикулярный вектор для крыльев стрелки
                    px = -dy
                    py = dx
                    
                    # Три точки треугольника стрелочки на конце линии перед фишкой
                    # (отступаем немного назад от фишки, чтобы стрелка была видна)
                    arrow_tip_x = p2_scr[0] - dx * 14
                    arrow_tip_y = p2_scr[1] - dy * 14
                    arrow_tip = (arrow_tip_x, arrow_tip_y)
                    
                    left_wing_x = arrow_tip_x - dx * 12 + px * 8
                    left_wing_y = arrow_tip_y - dy * 12 + py * 8
                    left_wing = (left_wing_x, left_wing_y)
                    
                    right_wing_x = arrow_tip_x - dx * 12 - px * 8
                    right_wing_y = arrow_tip_y - dy * 12 - py * 8
                    right_wing = (right_wing_x, right_wing_y)
                    
                    pygame.draw.polygon(self.screen, glow_color, [arrow_tip, left_wing, right_wing])


        # 3. Подсвечиваем доступные ходы для текущего игрока
        if not self.game_over:
            curr_pos = self.get_current_pos()
            p_start = self.to_screen_coords(curr_pos)
            for move in self.get_possible_moves():
                p_end = self.to_screen_coords(move)
                pygame.draw.line(self.screen, COLOR_POSSIBLE, p_start, p_end, 3)

        # 4. Рисуем фишки ВСЕХ участвующих игроков
        for i in range(self.num_players):
            # Если игрок выбыл, рисуем его фишку чуть меньше (радиус 6 вместо 10), как маркер
            radius = 10 if self.active_players[i] else 6
            pygame.draw.circle(self.screen, self.player_colors[i], self.to_screen_coords(self.positions[i]), radius)
        
        # 5. Рисуем СЧЕТЧИК ПОБЕД (Самая верхняя строка)
        # Будем рендерить текст по частям, чтобы покрасить каждый счет в цвет своего игрока
        score_font = pygame.font.SysFont(None, 24)
        current_x = PADDING
        
        for i in range(self.num_players):
            # Текст вида "P1: 3"
            score_text = f"P{i+1}: {self.scores[i]}"
            # Если это не последний игрок, добавим запятую и пробел для разделения
            if i < self.num_players - 1:
                score_text += ",  "
                
            rendered_score = score_font.render(score_text, True, self.player_colors[i])
            self.screen.blit(rendered_score, (current_x, 10))
            # Сдвигаем X для отрисовки счета следующего игрока
            current_x += rendered_score.get_width()

        # 6. Рисуем кнопку Рестарта (Смещена ниже, на Y = 38)
        self.restart_btn_rect = pygame.Rect(PADDING, 38, 30, 30)
        
        mouse_pos = pygame.mouse.get_pos()
        btn_color = (90, 90, 90) if self.restart_btn_rect.collidepoint(mouse_pos) else (70, 70, 70)
        pygame.draw.circle(self.screen, btn_color, (PADDING + 15, 38 + 15), 15)
        
        # Рендерим и поворачиваем символ стрелки
        arrow_font = pygame.font.SysFont(['segoeuisymbol', 'arial', 'sans'], 24)
        arrow_text = arrow_font.render("↻", True, COLOR_TEXT)
        rotated_arrow = pygame.transform.rotate(arrow_text, -90)
        
        # Центрируем стрелочку с учетом нового Y
        arrow_rect = rotated_arrow.get_rect(center=(PADDING + 18, 38 + 15))
        self.screen.blit(rotated_arrow, arrow_rect)

        # 7. Выводим текст состояния игры (Вровень с кнопкой рестарта, Y = 40)
        if self.game_over:
            text_str = f"Победил {self.winner}!"
            text_color = COLOR_TEXT
        else:
            name = self.player_names[self.current_idx]
            p_type = self.player_types[self.current_idx]
            
            is_bot = ""
            if p_type == "random_bot":
                is_bot = " (Рандом)"
            elif p_type == "smart_bot":
                is_bot = " (Умный)"
                
            text_str = f"Move: {name}{is_bot}"
            text_color = self.player_colors[self.current_idx]
                
        text = score_font.render(text_str, True, text_color)
        # Выводим текст правее кнопки на уровне Y = 40
        self.screen.blit(text, (PADDING + 50, 44))
        
        pygame.display.flip()


def main():
    print("=== Sticks Game ===")
    
    # 1. Запрос размера поля
    while True:
        try:
            size_input = int(input("Enter field size (from 2 to 15): ").strip())
            if 2 <= size_input <= 15:
                grid_size = size_input
                break  # Ввод верный, выходим из цикла
            else:
                print("Error! Only from 2 to 15. Try again.")
        except ValueError:
            print("Error! Enter correct integer number. Try again.")
    
    # 2. Запрос количества игроков
    while True:
        try:
            p_count = int(input("\nEnter number of players (from 2 to 4): ").strip())
            if 2 <= p_count <= 4:
                break
            else:
                print("Error! Only from 2 to 4 players.")
        except ValueError:
            print("Error! Enter correct integer number.")

    # 3. Настройка типов игроков
    # Игрок 1 всегда человек
    player_types = []
    player_names = ["Blue (P1)", "Red (P2)", "Green (P3)", "Yellow (P4)"]
    
    for i in range(p_count):
        while True:
            print(f"\nWho plays as {player_names[i]}?")
            print("1 - Human")
            print("2 - Random bot (Easy)")
            print("3 - Smart bot (Hard)")
            choice = input("Your choice (1, 2 or 3): ").strip()
            if choice == "1":
                player_types.append("human")
                break
            elif choice == "2":
                player_types.append("random_bot")
                break
            elif choice == "3":
                player_types.append("smart_bot")
                break
            else:
                print("Error! Enter only 1, 2 or 3.")

    game = Game(grid_size=grid_size, player_types=player_types)
    clock = pygame.time.Clock()

    while True:
        # Проверяем, должен ли ходить бот (любого типа)
        if not game.game_over and "bot" in game.player_types[game.current_idx]:
            game.bot_turn()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                game.handle_click(event.pos)

        game.draw()
        clock.tick(60)

if __name__ == "__main__":
    main()
