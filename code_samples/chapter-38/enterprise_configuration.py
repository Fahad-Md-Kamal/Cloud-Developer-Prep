"""
Enterprise Configuration Management with Standard Library

This module demonstrates production-grade configuration management using
Python's built-in configparser, argparse, and os modules for systems like
Lawstronaut (legal document processing) and Optimizely (AI-powered platforms).

Key concepts covered:
- Multi-environment configuration with hierarchical overrides
- Secure secret management and environment integration
- Advanced CLI development with argparse subcommands
- Configuration validation and type coercion
- Dynamic configuration reloading and monitoring

Real-world applications:
- Web crawler configuration across multiple legal jurisdictions
- A/B testing platform configuration for different environments
- Microservices configuration management and service discovery

Author: Technical Interview Preparation Guide
"""

import configparser
import argparse
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
import threading
import time
from datetime import datetime
import subprocess
import signal
from contextlib import contextmanager
import tempfile
import shutil
from abc import ABC, abstractmethod

# =============================================================================
# MULTI-ENVIRONMENT CONFIGURATION SYSTEM
# =============================================================================

@dataclass
class ConfigurationSchema:
    """Schema definition for configuration validation."""
    key: str
    type_: type
    required: bool = True
    default: Any = None
    validator: Optional[Callable[[Any], bool]] = None
    description: str = ""

class LegalCrawlerConfiguration:
    """
    Production-grade configuration management for legal document crawler.
    
    Demonstrates hierarchical configuration loading, environment-specific
    overrides, and secure secret management for enterprise systems.
    """
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = Path(config_dir or "config")
        self.config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        
        # Configuration schema for validation
        self.schema = {
            'crawler.rate_limit': ConfigurationSchema(
                'crawler.rate_limit', int, default=10,
                validator=lambda x: x > 0,
                description="Requests per second limit"
            ),
            'crawler.user_agent': ConfigurationSchema(
                'crawler.user_agent', str, 
                default="LegalCrawler/1.0",
                description="HTTP User-Agent string"
            ),
            'database.host': ConfigurationSchema(
                'database.host', str, default="localhost",
                description="Database host address"
            ),
            'database.port': ConfigurationSchema(
                'database.port', int, default=5432,
                validator=lambda x: 1 <= x <= 65535,
                description="Database port number"
            ),
            'security.api_key': ConfigurationSchema(
                'security.api_key', str, required=True,
                description="API authentication key"
            ),
            'logging.level': ConfigurationSchema(
                'logging.level', str, default="INFO",
                validator=lambda x: x.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                description="Logging level"
            )
        }
        
        self._config_lock = threading.Lock()
        self._load_timestamp = None
        
    def load_configuration(self, environment: str = "development") -> Dict[str, Any]:
        """
        Load configuration with hierarchical override system.
        
        Loading order (later overrides earlier):
        1. default.ini (base configuration)
        2. {environment}.ini (environment-specific)
        3. local.ini (local overrides - not in version control)
        4. Environment variables (highest priority)
        """
        with self._config_lock:
            # Clear existing configuration
            self.config.clear()
            
            # Define configuration files in priority order
            config_files = [
                self.config_dir / "default.ini",
                self.config_dir / f"{environment}.ini", 
                self.config_dir / "local.ini"
            ]
            
            # Load configuration files that exist
            loaded_files = []
            for config_file in config_files:
                if config_file.exists():
                    try:
                        self.config.read(config_file)
                        loaded_files.append(str(config_file))
                        logging.info(f"Loaded configuration: {config_file}")
                    except configparser.Error as e:
                        logging.error(f"Configuration error in {config_file}: {e}")
                        raise
            
            # Apply environment variable overrides
            self._apply_environment_overrides()
            
            # Validate configuration
            validation_errors = self._validate_configuration()
            if validation_errors:
                raise ValueError(f"Configuration validation errors: {validation_errors}")
            
            self._load_timestamp = datetime.now()
            
            return self._get_configuration_dict()
    
    def _apply_environment_overrides(self):
        """
        Apply environment variable overrides.
        
        Environment variables follow pattern: CRAWLER_SECTION_KEY
        Example: CRAWLER_DATABASE_HOST overrides [database] host
        """
        env_prefix = "CRAWLER_"
        
        for env_var, env_value in os.environ.items():
            if not env_var.startswith(env_prefix):
                continue
            
            # Parse environment variable to section and key
            config_path = env_var[len(env_prefix):].lower()
            parts = config_path.split('_', 1)
            
            if len(parts) != 2:
                continue
                
            section, key = parts
            
            # Ensure section exists
            if not self.config.has_section(section):
                self.config.add_section(section)
            
            # Set configuration value
            self.config.set(section, key, env_value)
            logging.debug(f"Applied environment override: {section}.{key} = {env_value}")
    
    def _validate_configuration(self) -> List[str]:
        """Validate configuration against schema."""
        errors = []
        
        for schema_key, schema in self.schema.items():
            section, key = schema_key.split('.', 1)
            
            # Check if value exists
            if self.config.has_option(section, key):
                raw_value = self.config.get(section, key)
                
                # Type coercion and validation
                try:
                    if schema.type_ == int:
                        value = self.config.getint(section, key)
                    elif schema.type_ == float:
                        value = self.config.getfloat(section, key)
                    elif schema.type_ == bool:
                        value = self.config.getboolean(section, key)
                    else:
                        value = raw_value
                    
                    # Custom validation
                    if schema.validator and not schema.validator(value):
                        errors.append(f"{schema_key}: validation failed for value '{value}'")
                        
                except ValueError as e:
                    errors.append(f"{schema_key}: type conversion error - {e}")
                    
            elif schema.required and schema.default is None:
                errors.append(f"{schema_key}: required configuration missing")
        
        return errors
    
    def _get_configuration_dict(self) -> Dict[str, Any]:
        """Convert ConfigParser to nested dictionary with type coercion."""
        config_dict = {}
        
        for section_name in self.config.sections():
            config_dict[section_name] = {}
            for key, value in self.config.items(section_name):
                # Apply type coercion based on schema
                schema_key = f"{section_name}.{key}"
                if schema_key in self.schema:
                    schema = self.schema[schema_key]
                    if schema.type_ == int:
                        value = self.config.getint(section_name, key)
                    elif schema.type_ == float:
                        value = self.config.getfloat(section_name, key)
                    elif schema.type_ == bool:
                        value = self.config.getboolean(section_name, key)
                
                config_dict[section_name][key] = value
        
        return config_dict
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation (e.g., 'database.host')."""
        try:
            section, option = key.split('.', 1)
            if self.config.has_option(section, option):
                # Apply type coercion based on schema
                if key in self.schema:
                    schema = self.schema[key]
                    if schema.type_ == int:
                        return self.config.getint(section, option)
                    elif schema.type_ == float:
                        return self.config.getfloat(section, option)
                    elif schema.type_ == bool:
                        return self.config.getboolean(section, option)
                
                return self.config.get(section, option)
        except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
            pass
        
        # Return default from schema or provided default
        if key in self.schema and self.schema[key].default is not None:
            return self.schema[key].default
        
        return default
    
    @contextmanager
    def temporary_override(self, overrides: Dict[str, Any]):
        """
        Temporarily override configuration values.
        
        Useful for testing or feature flags.
        """
        original_values = {}
        
        try:
            # Apply overrides and store original values
            for key, value in overrides.items():
                original_values[key] = self.get(key)
                section, option = key.split('.', 1)
                
                if not self.config.has_section(section):
                    self.config.add_section(section)
                
                self.config.set(section, option, str(value))
            
            yield
            
        finally:
            # Restore original values
            for key, original_value in original_values.items():
                if original_value is not None:
                    section, option = key.split('.', 1)
                    self.config.set(section, option, str(original_value))

# =============================================================================
# ADVANCED CLI FRAMEWORK WITH SUBCOMMANDS
# =============================================================================

class CLICommand(ABC):
    """Abstract base class for CLI commands."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description."""
        pass
    
    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser):
        """Add command-specific arguments to parser."""
        pass
    
    @abstractmethod
    def execute(self, args: argparse.Namespace, config: Dict[str, Any]) -> int:
        """Execute command. Return 0 for success, non-zero for error."""
        pass

class CrawlerStartCommand(CLICommand):
    """Command to start the legal document crawler."""
    
    @property
    def name(self) -> str:
        return "start"
    
    @property
    def description(self) -> str:
        return "Start the legal document crawler"
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--jurisdictions", 
            nargs="+", 
            default=["US", "EU", "UK"],
            help="Jurisdictions to crawl (default: US EU UK)"
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=1000,
            help="Maximum pages to crawl per jurisdiction"
        )
        parser.add_argument(
            "--parallel",
            type=int,
            default=4,
            help="Number of parallel crawler workers"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be crawled without actually crawling"
        )
    
    def execute(self, args: argparse.Namespace, config: Dict[str, Any]) -> int:
        """Execute crawler start command."""
        print(f"Starting legal document crawler...")
        print(f"Jurisdictions: {', '.join(args.jurisdictions)}")
        print(f"Max pages per jurisdiction: {args.max_pages}")
        print(f"Parallel workers: {args.parallel}")
        print(f"Rate limit: {config.get('crawler', {}).get('rate_limit', 10)} req/sec")
        
        if args.dry_run:
            print("DRY RUN: Would start crawler with above configuration")
            return 0
        
        # Simulate crawler start
        for i, jurisdiction in enumerate(args.jurisdictions):
            print(f"[{i+1}/{len(args.jurisdictions)}] Starting crawler for {jurisdiction}...")
            time.sleep(0.5)  # Simulate startup time
        
        print("All crawlers started successfully!")
        return 0

class DatabaseMigrateCommand(CLICommand):
    """Command to run database migrations."""
    
    @property
    def name(self) -> str:
        return "migrate"
    
    @property
    def description(self) -> str:
        return "Run database migrations"
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--target",
            help="Target migration version"
        )
        parser.add_argument(
            "--fake",
            action="store_true", 
            help="Mark migrations as applied without running them"
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List available migrations"
        )
    
    def execute(self, args: argparse.Namespace, config: Dict[str, Any]) -> int:
        """Execute database migration command."""
        if args.list:
            migrations = [
                "001_initial_schema",
                "002_add_indexes", 
                "003_add_jurisdiction_table",
                "004_add_full_text_search"
            ]
            print("Available migrations:")
            for migration in migrations:
                print(f"  {migration}")
            return 0
        
        db_config = config.get('database', {})
        print(f"Connecting to database: {db_config.get('host', 'localhost')}:{db_config.get('port', 5432)}")
        
        if args.fake:
            print("Marking migrations as applied (fake mode)")
        else:
            print("Running database migrations...")
            time.sleep(1)  # Simulate migration time
        
        target = args.target or "latest"
        print(f"Migrated to: {target}")
        return 0

class ConfigShowCommand(CLICommand):
    """Command to show current configuration."""
    
    @property
    def name(self) -> str:
        return "config"
    
    @property
    def description(self) -> str:
        return "Show current configuration"
    
    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--section",
            help="Show only specified section"
        )
        parser.add_argument(
            "--key", 
            help="Show only specified key (requires --section)"
        )
        parser.add_argument(
            "--format",
            choices=["ini", "json", "table"],
            default="table",
            help="Output format"
        )
    
    def execute(self, args: argparse.Namespace, config: Dict[str, Any]) -> int:
        """Execute configuration show command."""
        if args.key and not args.section:
            print("Error: --key requires --section", file=sys.stderr)
            return 1
        
        # Filter configuration
        if args.section:
            if args.section not in config:
                print(f"Error: Section '{args.section}' not found", file=sys.stderr)
                return 1
            
            section_config = config[args.section]
            if args.key:
                if args.key not in section_config:
                    print(f"Error: Key '{args.key}' not found in section '{args.section}'", file=sys.stderr)
                    return 1
                display_config = {args.section: {args.key: section_config[args.key]}}
            else:
                display_config = {args.section: section_config}
        else:
            display_config = config
        
        # Output in requested format
        if args.format == "json":
            print(json.dumps(display_config, indent=2, default=str))
        elif args.format == "ini":
            # Convert back to INI format
            for section, values in display_config.items():
                print(f"[{section}]")
                for key, value in values.items():
                    print(f"{key} = {value}")
                print()
        else:  # table format
            for section, values in display_config.items():
                print(f"\n[{section}]")
                for key, value in values.items():
                    print(f"  {key:<20} = {value}")
        
        return 0

class LegalCrawlerCLI:
    """
    Advanced CLI framework for legal document crawler management.
    
    Demonstrates argparse subcommands, configuration integration,
    and production-ready command-line tool development.
    """
    
    def __init__(self):
        self.commands = {}
        self.config_manager = None
        
        # Register built-in commands
        self.register_command(CrawlerStartCommand())
        self.register_command(DatabaseMigrateCommand())
        self.register_command(ConfigShowCommand())
        
    def register_command(self, command: CLICommand):
        """Register a new CLI command."""
        self.commands[command.name] = command
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create main argument parser with subcommands."""
        parser = argparse.ArgumentParser(
            prog="legal-crawler",
            description="Legal Document Crawler Management Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  legal-crawler start --jurisdictions US EU --max-pages 5000
  legal-crawler migrate --list
  legal-crawler config --section database --format json
  
For more information, see: https://lawstronaut.com/docs/crawler
            """
        )
        
        # Global arguments
        parser.add_argument(
            "--config-dir",
            type=Path,
            default=Path("config"),
            help="Configuration directory (default: config)"
        )
        parser.add_argument(
            "--environment", 
            default="development",
            help="Environment name (default: development)"
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Logging level (default: INFO)"
        )
        parser.add_argument(
            "--version",
            action="version",
            version="Legal Crawler 1.0.0"
        )
        
        # Create subparsers
        subparsers = parser.add_subparsers(
            dest="command",
            help="Available commands",
            metavar="COMMAND"
        )
        
        # Add registered commands
        for command in self.commands.values():
            cmd_parser = subparsers.add_parser(
                command.name,
                help=command.description,
                description=command.description
            )
            command.add_arguments(cmd_parser)
        
        return parser
    
    def setup_logging(self, level: str):
        """Configure logging system."""
        numeric_level = getattr(logging, level.upper())
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def load_configuration(self, config_dir: Path, environment: str) -> Dict[str, Any]:
        """Load and validate configuration."""
        self.config_manager = LegalCrawlerConfiguration(config_dir)
        return self.config_manager.load_configuration(environment)
    
    def run(self, args: List[str] = None) -> int:
        """Run CLI application."""
        parser = self.create_parser()
        
        # Parse arguments
        if args is None:
            args = sys.argv[1:]
        
        parsed_args = parser.parse_args(args)
        
        # Setup logging
        self.setup_logging(parsed_args.log_level)
        
        # Check if command was provided
        if not parsed_args.command:
            parser.print_help()
            return 1
        
        try:
            # Load configuration
            config = self.load_configuration(parsed_args.config_dir, parsed_args.environment)
            logging.info(f"Loaded configuration for environment: {parsed_args.environment}")
            
            # Execute command
            command = self.commands[parsed_args.command]
            return command.execute(parsed_args, config)
            
        except Exception as e:
            logging.error(f"Command execution failed: {e}")
            if parsed_args.log_level == "DEBUG":
                import traceback
                traceback.print_exc()
            return 1

# =============================================================================
# CONFIGURATION FILE TEMPLATES AND SAMPLES
# =============================================================================

def create_sample_configuration_files(config_dir: Path):
    """Create sample configuration files for demonstration."""
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Default configuration
    default_config = """
# Default configuration for Legal Document Crawler
# This file contains base settings that are common across all environments

[crawler]
rate_limit = 10
user_agent = LegalCrawler/1.0
timeout = 30
retry_attempts = 3
concurrent_workers = 4

[database]
host = localhost
port = 5432
name = legal_documents
pool_size = 10
max_overflow = 20

[logging]
level = INFO
format = %(asctime)s - %(name)s - %(levelname)s - %(message)s
file_path = logs/crawler.log
max_file_size = 10MB
backup_count = 5

[security]
# API key should be set via environment variable: CRAWLER_SECURITY_API_KEY
api_key = your_api_key_here

[storage]
base_path = /var/lib/legal-crawler/documents
temp_path = /tmp/legal-crawler
archive_path = /var/lib/legal-crawler/archive
"""
    
    # Production configuration
    production_config = """
# Production environment configuration
# Overrides default.ini for production deployment

[crawler]
rate_limit = 5
concurrent_workers = 8
timeout = 60

[database] 
host = db.production.example.com
port = 5432
pool_size = 20
max_overflow = 50

[logging]
level = WARNING
file_path = /var/log/legal-crawler/crawler.log

[storage]
base_path = /data/legal-crawler/documents
temp_path = /data/legal-crawler/temp
archive_path = /data/legal-crawler/archive
"""
    
    # Development configuration  
    development_config = """
# Development environment configuration
# Overrides default.ini for local development

[crawler]
rate_limit = 2
concurrent_workers = 2

[database]
host = localhost
name = legal_documents_dev

[logging]
level = DEBUG

[storage]
base_path = ./dev_data/documents
temp_path = ./dev_data/temp
archive_path = ./dev_data/archive
"""
    
    # Write configuration files
    (config_dir / "default.ini").write_text(default_config)
    (config_dir / "production.ini").write_text(production_config) 
    (config_dir / "development.ini").write_text(development_config)
    
    # Create secrets file (would not be in version control)
    secrets_content = """
# Local secrets and overrides
# This file should not be committed to version control

[security]
api_key = dev_api_key_12345

[database]
password = dev_password
"""
    (config_dir / "local.ini").write_text(secrets_content)

# =============================================================================
# DEMONSTRATION AND INTEGRATION
# =============================================================================

def demonstrate_enterprise_configuration():
    """
    Comprehensive demonstration of enterprise configuration management
    patterns using Python standard library.
    """
    
    print("=== Enterprise Configuration Management with Standard Library ===\n")
    
    # Create temporary directory for demonstration
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        
        # 1. Configuration System Setup
        print("1. Multi-Environment Configuration System")
        
        create_sample_configuration_files(config_dir)
        print(f"Created sample configuration files in: {config_dir}")
        
        # Show created files
        for config_file in config_dir.glob("*.ini"):
            print(f"  - {config_file.name}")
        
        # 2. Configuration Loading and Validation
        print("\n2. Configuration Loading with Validation")
        
        config_manager = LegalCrawlerConfiguration(config_dir)
        
        # Test different environments
        for environment in ["development", "production"]:
            print(f"\nLoading {environment} configuration:")
            
            try:
                config = config_manager.load_configuration(environment)
                print(f"  ✓ Successfully loaded {len(config)} sections")
                
                # Show key configuration values
                print(f"  Database host: {config_manager.get('database.host')}")
                print(f"  Crawler rate limit: {config_manager.get('crawler.rate_limit')}")
                print(f"  Log level: {config_manager.get('logging.level')}")
                
            except Exception as e:
                print(f"  ✗ Configuration error: {e}")
        
        # 3. Environment Variable Overrides
        print("\n3. Environment Variable Override System")
        
        # Set environment variables
        os.environ["CRAWLER_DATABASE_HOST"] = "override.example.com"
        os.environ["CRAWLER_CRAWLER_RATE_LIMIT"] = "15"
        
        config = config_manager.load_configuration("development")
        
        print("Environment variable overrides applied:")
        print(f"  Database host: {config_manager.get('database.host')} (from ENV)")
        print(f"  Rate limit: {config_manager.get('crawler.rate_limit')} (from ENV)")
        
        # Clean up environment variables
        del os.environ["CRAWLER_DATABASE_HOST"]
        del os.environ["CRAWLER_CRAWLER_RATE_LIMIT"]
        
        # 4. Temporary Configuration Overrides
        print("\n4. Temporary Configuration Overrides")
        
        print(f"Original rate limit: {config_manager.get('crawler.rate_limit')}")
        
        with config_manager.temporary_override({"crawler.rate_limit": 100}):
            print(f"Temporary rate limit: {config_manager.get('crawler.rate_limit')}")
        
        print(f"Restored rate limit: {config_manager.get('crawler.rate_limit')}")
        
        # 5. Advanced CLI Framework
        print("\n5. Advanced CLI Framework with Subcommands")
        
        cli = LegalCrawlerCLI()
        
        # Test different CLI commands
        test_commands = [
            ["--help"],
            ["config", "--section", "database"],
            ["start", "--jurisdictions", "US", "EU", "--dry-run"],
            ["migrate", "--list"]
        ]
        
        for cmd_args in test_commands:
            print(f"\nTesting command: legal-crawler {' '.join(cmd_args)}")
            try:
                with tempfile.TemporaryDirectory() as cli_temp_dir:
                    cli_config_dir = Path(cli_temp_dir) / "config"
                    create_sample_configuration_files(cli_config_dir)
                    
                    # Add config directory to command args
                    full_args = ["--config-dir", str(cli_config_dir)] + cmd_args
                    
                    result = cli.run(full_args)
                    print(f"Command result: {'SUCCESS' if result == 0 else 'FAILED'}")
                    
            except SystemExit:
                print("Command completed (help or error)")
            except Exception as e:
                print(f"Command error: {e}")
        
        # 6. Configuration Performance and Monitoring
        print("\n6. Configuration Performance Metrics")
        
        # Test configuration loading performance
        start_time = time.perf_counter()
        for i in range(100):
            config = config_manager.load_configuration("development")
        load_time = time.perf_counter() - start_time
        
        print(f"Configuration loading performance:")
        print(f"  100 loads in {load_time:.4f}s")
        print(f"  Average: {load_time * 10:.2f}ms per load")
        print(f"  Rate: {100 / load_time:.0f} loads/second")
        
        # Test configuration access performance
        start_time = time.perf_counter()
        for i in range(1000):
            value = config_manager.get('database.host')
        access_time = time.perf_counter() - start_time
        
        print(f"Configuration access performance:")
        print(f"  1000 gets in {access_time:.4f}s")
        print(f"  Average: {access_time:.3f}ms per get")
        print(f"  Rate: {1000 / access_time:.0f} gets/second")
    
    print("\n=== All enterprise configuration patterns successfully demonstrated ===")

if __name__ == "__main__":
    # Configure logging for demonstration
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run demonstration
    demonstrate_enterprise_configuration()