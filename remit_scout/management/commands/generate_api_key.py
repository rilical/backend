"""
Management command to generate and manage API keys.

This command allows administrators to:
- Create new API keys for clients/partners
- List existing API keys
- Revoke or update existing keys
"""
import os
import uuid
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from remit_scout.models import APIKey


class Command(BaseCommand):
    help = "Generate and manage API keys for RemitScout API access"

    def add_arguments(self, parser):
        # Define command actions as subcommands
        subparsers = parser.add_subparsers(dest="action", help="Action to perform")
        
        # Create a new API key
        create_parser = subparsers.add_parser("create", help="Create a new API key")
        create_parser.add_argument(
            "--name", required=True, 
            help="Name of the client/partner"
        )
        create_parser.add_argument(
            "--email", 
            help="Contact email for the client/partner"
        )
        create_parser.add_argument(
            "--tier", choices=["registered", "premium", "enterprise"], default="registered",
            help="Access tier for the API key"
        )
        create_parser.add_argument(
            "--expires", type=int, 
            help="Days until the API key expires (leave empty for no expiration)"
        )
        create_parser.add_argument(
            "--rate-limit", type=int, 
            help="Custom rate limit (requests per minute)"
        )
        
        # List existing API keys
        list_parser = subparsers.add_parser("list", help="List existing API keys")
        list_parser.add_argument(
            "--active-only", action="store_true",
            help="Only show active API keys"
        )
        list_parser.add_argument(
            "--tier", choices=["registered", "premium", "enterprise"],
            help="Filter by tier"
        )
        list_parser.add_argument(
            "--format", choices=["table", "json"], default="table",
            help="Output format"
        )
        
        # Revoke an API key
        revoke_parser = subparsers.add_parser("revoke", help="Revoke an API key")
        revoke_parser.add_argument(
            "key", help="API key to revoke"
        )
        
        # Update an API key
        update_parser = subparsers.add_parser("update", help="Update an API key")
        update_parser.add_argument(
            "key", help="API key to update"
        )
        update_parser.add_argument(
            "--name", help="New name for the client/partner"
        )
        update_parser.add_argument(
            "--email", help="New contact email"
        )
        update_parser.add_argument(
            "--tier", choices=["registered", "premium", "enterprise"],
            help="New access tier"
        )
        update_parser.add_argument(
            "--expires", type=int,
            help="New expiration (days from now, use 0 to remove expiration)"
        )
        update_parser.add_argument(
            "--rate-limit", type=int,
            help="New rate limit (requests per minute)"
        )
        update_parser.add_argument(
            "--activate", action="store_true",
            help="Activate a previously deactivated key"
        )
        update_parser.add_argument(
            "--deactivate", action="store_true",
            help="Temporarily deactivate the key"
        )

    def handle(self, *args, **options):
        action = options.get("action")
        
        if not action:
            self.stdout.write(self.style.ERROR("Please specify an action: create, list, revoke, or update"))
            return
            
        if action == "create":
            self._create_api_key(options)
        elif action == "list":
            self._list_api_keys(options)
        elif action == "revoke":
            self._revoke_api_key(options)
        elif action == "update":
            self._update_api_key(options)
        else:
            self.stdout.write(self.style.ERROR(f"Unknown action: {action}"))

    def _create_api_key(self, options):
        """Create a new API key"""
        name = options.get("name")
        email = options.get("email")
        tier = options.get("tier", "registered")
        expires_days = options.get("expires")
        rate_limit = options.get("rate_limit")
        
        # Generate a new API key
        key = uuid.uuid4().hex
        
        # Set expiration date if provided
        expires_at = None
        if expires_days is not None:
            expires_at = timezone.now() + timedelta(days=expires_days)
        
        # Create the API key
        api_key = APIKey.objects.create(
            key=key,
            name=name,
            email=email,
            tier=tier,
            expires_at=expires_at,
            rate_limit=rate_limit or self._get_default_rate_limit(tier),
        )
        
        self.stdout.write(self.style.SUCCESS(f"Created new API key for {name}"))
        self.stdout.write(f"Key: {key}")
        self.stdout.write(f"Tier: {tier}")
        self.stdout.write(f"Rate limit: {api_key.rate_limit} requests/minute")
        
        if expires_at:
            self.stdout.write(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.stdout.write("Expires: Never")
            
        self.stdout.write("\nIMPORTANT: Store this key securely as it cannot be retrieved later!")

    def _list_api_keys(self, options):
        """List existing API keys"""
        active_only = options.get("active_only", False)
        tier_filter = options.get("tier")
        output_format = options.get("format", "table")
        
        # Build query filters
        filters = {}
        if active_only:
            filters['is_active'] = True
            filters['revoked_at__isnull'] = True
            
            # Also check expiration
            filters['expires_at__isnull'] = True
            filters['expires_at__gt'] = timezone.now()
            
        if tier_filter:
            filters['tier'] = tier_filter
            
        # Get API keys
        api_keys = APIKey.objects.filter(**filters).order_by('-created_at')
        
        if not api_keys.exists():
            self.stdout.write(self.style.WARNING("No API keys found matching the criteria."))
            return
            
        # Output in requested format
        if output_format == "json":
            self._output_json(api_keys)
        else:
            self._output_table(api_keys)

    def _output_table(self, api_keys):
        """Output API keys as a formatted table"""
        from tabulate import tabulate
        
        headers = ["Name", "Key (first 8 chars)", "Tier", "Status", "Created", "Expires", "Requests"]
        rows = []
        
        for api_key in api_keys:
            # Determine status
            status = "Active"
            if not api_key.is_active:
                status = "Inactive"
            elif api_key.revoked_at:
                status = "Revoked"
            elif api_key.expires_at and api_key.expires_at < timezone.now():
                status = "Expired"
                
            # Format dates
            created = api_key.created_at.strftime("%Y-%m-%d")
            expires = api_key.expires_at.strftime("%Y-%m-%d") if api_key.expires_at else "Never"
                
            # Add row
            rows.append([
                api_key.name,
                api_key.key[:8] + "...",
                api_key.tier,
                status,
                created,
                expires,
                api_key.total_requests,
            ])
            
        self.stdout.write(tabulate(rows, headers, tablefmt="pretty"))
        self.stdout.write(f"\nTotal: {len(rows)} API keys")

    def _output_json(self, api_keys):
        """Output API keys as JSON"""
        import json
        
        keys_data = []
        for api_key in api_keys:
            keys_data.append({
                "id": str(api_key.id),
                "name": api_key.name,
                "key_preview": api_key.key[:8] + "...",
                "tier": api_key.tier,
                "is_active": api_key.is_active,
                "created_at": api_key.created_at.isoformat(),
                "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                "revoked_at": api_key.revoked_at.isoformat() if api_key.revoked_at else None,
                "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                "rate_limit": api_key.rate_limit,
                "total_requests": api_key.total_requests,
            })
            
        self.stdout.write(json.dumps(keys_data, indent=2))

    def _revoke_api_key(self, options):
        """Revoke an API key"""
        key = options.get("key")
        
        try:
            api_key = APIKey.objects.get(key=key)
        except APIKey.DoesNotExist:
            raise CommandError(f"API key not found: {key}")
            
        # Revoke the key
        api_key.revoked_at = timezone.now()
        api_key.is_active = False
        api_key.save()
        
        self.stdout.write(self.style.SUCCESS(f"API key for {api_key.name} has been revoked."))

    def _update_api_key(self, options):
        """Update an API key"""
        key = options.get("key")
        
        try:
            api_key = APIKey.objects.get(key=key)
        except APIKey.DoesNotExist:
            raise CommandError(f"API key not found: {key}")
            
        # Update fields if provided
        if options.get("name"):
            api_key.name = options.get("name")
            
        if options.get("email"):
            api_key.email = options.get("email")
            
        if options.get("tier"):
            api_key.tier = options.get("tier")
            # Update rate limit to match tier unless custom rate limit provided
            if not options.get("rate_limit"):
                api_key.rate_limit = self._get_default_rate_limit(options.get("tier"))
            
        if options.get("rate_limit"):
            api_key.rate_limit = options.get("rate_limit")
            
        # Handle expiration
        if options.get("expires") is not None:
            expires_days = options.get("expires")
            if expires_days == 0:
                api_key.expires_at = None
            else:
                api_key.expires_at = timezone.now() + timedelta(days=expires_days)
                
        # Handle activation/deactivation
        if options.get("activate"):
            api_key.is_active = True
        elif options.get("deactivate"):
            api_key.is_active = False
            
        # Save changes
        api_key.save()
        
        self.stdout.write(self.style.SUCCESS(f"API key for {api_key.name} has been updated."))
        
    def _get_default_rate_limit(self, tier):
        """Get the default rate limit for a tier"""
        if tier == "enterprise":
            return 2000
        elif tier == "premium":
            return 1000
        else:
            return 300 