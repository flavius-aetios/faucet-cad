# Проставка для кухонного смесителя

Параметрическая модель CadQuery, которая меняет наклон выдвижной лейки,
чтобы направить струю вертикально. Текущий вариант рассчитан на коррекцию **13°**
по фотографии и посадочную часть лейки **Ø22 × 23 мм**.

![Вариант v2 и условная схема установки](output/flush_v2/preview.png)

**Состояние на 18.09.2026:** выбраны нижний **IN 22.6** и верхний **OUT 23.0**.
Подготовлен [вариант v2 для согласования и анализ печати](PROPOSAL_V2.md):
корпус Ø28,5 мм заподлицо на стыках, паз 12 мм, скругления R0,6 мм.
Новые STL/STEP находятся в **[output/flush_v2](output/flush_v2/)**;
старые файлы в корне `output/` сохранены для сравнения.
Результаты примерок записаны в [FIT_LOG.md](FIT_LOG.md).
Внутренний диаметр излива измерен: **22,5 мм**. Цель — плотная верхняя посадка
адаптера и свободное скольжение лейки в нижней. Надёжность удержания и фактическое
направление струи предстоит проверить. STL уточнён после замечания о видимых гранях.

## Что сохранено

- [model.py](model.py) — исходник модели; [parameters_flush_v2.json](parameters_flush_v2.json) —
  предлагаемые размеры; [parameters.json](parameters.json) — предыдущий вариант.
- [Фото референсы](<Фото референсы/>) — все четыре исходные фотографии с замерами.
- [output/flush_v2](output/flush_v2/) — новая полная проставка и два контрольных образца,
  условная сборка, изображения и отчёты; [output](output/) — также предыдущая серия.
- [PROPOSAL_V2.md](PROPOSAL_V2.md) — изменения, анализ сопла 0,4 мм и выбор PLA/PETG;
  [DESIGN.md](DESIGN.md) — исходная конструкция и история настройки окружения.
- `.vscode/` — настройки Python/OCP CAD Viewer и запуск через Ctrl+Shift+B.
- `pyproject.toml`, `uv.lock`, `.python-version` — воспроизводимое Python-окружение.

Папки `.venv`, кэши и временные диагностические установки в Git не включены:
окружение создаётся заново на другом компьютере из `uv.lock`.
STL уже можно открыть в Bambu Studio без установки CadQuery.

## Открыть на другом компьютере: Windows / PowerShell

Нужны Git, [uv](https://docs.astral.sh/uv/getting-started/installation/) и VS Code.
Для доступа к приватному репозиторию войти в свой аккаунт GitHub.

```powershell
git clone https://github.com/flavius-aetios/faucet-cad.git
Set-Location faucet-cad
uv sync --locked --cache-dir .uv-cache
code --install-extension ms-python.python
code --install-extension ms-toolsai.jupyter
code --install-extension bernhard-42.ocp-cad-viewer
code .
```

`uv` создаёт `.venv` с Python 3.11 и версиями библиотек из lock-файла.
Путь клонирования может быть любым: настройки проекта используют `${workspaceFolder}`.
Открывать в VS Code нужно **папку проекта**, чтобы её настройки применились.

1. Если VS Code не выбрал Python автоматически, выполнить `Python: Select Interpreter`
   и выбрать `.venv\Scripts\python.exe` внутри клонированной папки.
2. Открыть `model.py`: справа должен открыться OCP CAD Viewer.
3. Для нового варианта: **Terminal → Run Task → OCP: Show flush rounded v2 proposal**.
   **Ctrl+Shift+B** показывает прежнюю модель для сравнения. Открытие исходника само
   по себе не отправляет модель; задача выполняет программу с `--view`.

Альтернатива из терминала в папке проекта:

```powershell
& '.\.venv\Scripts\python.exe' '.\model.py' --parameters parameters_flush_v2.json --output-dir output/flush_v2 --view
```

Для генерации файлов без Viewer и проверки результата:

```powershell
& '.\.venv\Scripts\python.exe' '.\check_environment.py'
& '.\.venv\Scripts\python.exe' '.\model.py' --parameters parameters_flush_v2.json --output-dir output/flush_v2
& '.\.venv\Scripts\python.exe' '.\verify_exports.py' --output-dir output/flush_v2
& '.\.venv\Scripts\python.exe' '.\analyze_print.py' --output-dir output/flush_v2
```

Сохранённые отчёты относятся к исходному компьютеру; эти команды обновляют их
по результатам проверок на новом компьютере.

## Уже исправленные проблемы окружения

- **Python падает при завершении:** на Windows совместная загрузка CasADi 3.8.0
  и NLopt 2.11.0 приводила к `0xC0000005`. Зафиксирована проверенная пара
  **CasADi 3.8.0 / NLopt 2.9.1**. Использовать `uv sync --locked`, чтобы сохранить её.
- **PowerShell: неожиданный токен `-m`:** расширению задан префикс `& ` через
  `OcpCadViewer.advanced.shellCommandPrefix`. После изменения настроек выполнить
  `Developer: Reload Window`. В ручных командах перед путём к Python в кавычках
  также нужен `&`.
- **В Viewer логотип OCP:** выполнить `model.py --view` или Ctrl+Shift+B.

Инструкции и настройки VS Code проверены на Windows с PowerShell. При переносе
на Linux/macOS путь к Python — `.venv/bin/python`; нужно также изменить Windows-путь
в `.vscode/tasks.json`/`settings.json` и убрать PowerShell-префикс `& `.

## Следующий шаг: контрольные образцы v2

Для рабочей детали предлагается PETG, PLA подходит для примерок. Изменение
материала, паза и толщины стенок требует проверки посадок на новой геометрии.
Сначала напечатать в выбранном материале:

- [OUT 23.0 v2](output/flush_v2/pin_gauge_OD_23.0.stl) — верхняя посадка длиной 20 мм.
- [IN 22.6 v2](output/flush_v2/socket_gauge_ID_22.6.stl) — короткий нижний образец.

На всех образцах есть выпуклые подписи: **IN** — внутренний диаметр,
**OUT** — наружный, затем размер в миллиметрах. Образцы можно печатать вместе
на одной пластине и различать по надписям. [Пример маркировки](output/flush_v2/labeled_samples.png).
Штрихи утолщены до **1 мм**, точка увеличена до **1,2 мм**, рельеф — **0,8 мм**.
Новая серия лежит отдельно от старой; надписи обозначают размер, а не ревизию.

Для сопла 0,4 мм: слой 0,2 мм, 4 стенки, масштаб 100%. Проверить каждый образец
рукой без запрессовки: не входит / входит плотно / есть люфт. По результату изменить
зазоры в `parameters_flush_v2.json`, затем пересоздать вариант v2.

Адаптер должен оставаться в изливе при извлечении лейки. Отдельной защёлки пока нет:
верхняя посадка удерживается трением, возвратный шланг возвращает лейку в адаптер.
Анализ стенок и нависаний, настройки и порядок установки описаны
в [PROPOSAL_V2.md](PROPOSAL_V2.md).

## Сохранить дальнейшие изменения

После изменения размеров и повторной генерации:

```powershell
git add .
git commit -m "Update adapter dimensions and printable models"
git push
```

На другом компьютере перед началом работы: `git pull`, затем
`uv sync --locked --cache-dir .uv-cache`.
