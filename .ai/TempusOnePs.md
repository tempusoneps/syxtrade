# TempusOnePs
 ________                                                      ______                       _______
/        |                                                    /      \                     /       \
$$$$$$$$/______   _____  ____    ______   __    __   _______ /$$$$$$  | _______    ______  $$$$$$$  | _______
   $$ | /      \ /     \/    \  /      \ /  |  /  | /       |$$ |  $$ |/       \  /      \ $$ |__$$ |/       |
   $$ |/$$$$$$  |$$$$$$ $$$$  |/$$$$$$  |$$ |  $$ |/$$$$$$$/ $$ |  $$ |$$$$$$$  |/$$$$$$  |$$    $$//$$$$$$$/
   $$ |$$    $$ |$$ | $$ | $$ |$$ |  $$ |$$ |  $$ |$$      \ $$ |  $$ |$$ |  $$ |$$    $$ |$$$$$$$/ $$      \
   $$ |$$$$$$$$/ $$ | $$ | $$ |$$ |__$$ |$$ \__$$ | $$$$$$  |$$ \__$$ |$$ |  $$ |$$$$$$$$/ $$ |      $$$$$$  |
   $$ |$$       |$$ | $$ | $$ |$$    $$/ $$    $$/ /     $$/ $$    $$/ $$ |  $$ |$$       |$$ |     /     $$/
   $$/  $$$$$$$/ $$/  $$/  $$/ $$$$$$$/   $$$$$$/  $$$$$$$/   $$$$$$/  $$/   $$/  $$$$$$$/ $$/      $$$$$$$/
                               $$ |                                              Quant & Algo Trading Platform
                               $$ |
                               $$/
--------------------------------------------------------------------------------------------------------------
## System structures
📦 TempusOnePs/
│
├── config/
│   ├── config.json               # Pipeline definition & scheduling
│   └── config.sample.json
│
├── core/
│   ├── scheduler.py              # Job scheduler (cron/interval)
│   ├── service_loader.py         # Dynamic service loader
│   ├── utils.py                  # Utility functions
│   └── service/                  # Base classes for services
│       ├── base_service.py       # Base service class
│       ├── base_signal.py        # Base signal class
│       └── base_execution.py     # Base execution class
│
├── docs/                         # Documentation
│
├── lib/                          # External libraries & APIs
│   ├── brokers/                  # Broker integrations (DNSE, Entrade)
│   ├── stock_price_patterns/     # Candlestick pattern recognition
│   └── telegram_api.py           # Telegram integration
│
├── modules/                      # Service implementations (Data, Signals, Execution, Log)
│   └── examples/                 # Example services
│
├── tools/                        # Utility scripts
│
├── run.py                        # Main entry point (single run)
├── run-cron.py                   # Scheduler entry point
├── pyproject.toml                # Project configuration & dependencies
└── README.md