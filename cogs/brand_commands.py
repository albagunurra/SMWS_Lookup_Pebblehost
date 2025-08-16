import json
import discord
from discord import app_commands
from discord.ext import commands
from difflib import get_close_matches
import traceback
import logging

logger = logging.getLogger('discord')

class BrandCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.brands = {}
            self.distillery_codes = {}
            self.load_brands()
            self.name_variants = {}
            self.initialize_name_variants()
            logger.info(f"BrandCommands initialized with {len(self.brands)} codes")
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}\n{traceback.format_exc()}")
            raise

    def load_brands(self):
        try:
            logger.debug("Attempting to load brands.json")
            with open('data/brands.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for brand in data['brands']:
                    brand_info = {
                        'name': brand['name'],
                        'details': brand.get('details', {}),
                        'region': brand.get('region', ''),
                        'style': brand.get('style', '')
                    }
                    
                    for code in brand['codes']:
                        self.brands[str(code)] = brand_info.copy()
                        if 'id' in brand and str(brand['id']) == str(code):
                            self.brands[str(code)]['details'] = brand.get('details', {})
                    
                    distillery_name = brand['name'].lower()
                    if distillery_name not in self.distillery_codes:
                        self.distillery_codes[distillery_name] = set()
                    self.distillery_codes[distillery_name].add(str(brand['id']))
                
                logger.info(f"Loaded {len(self.brands)} codes for {len(self.distillery_codes)} distilleries")
        except Exception as e:
            logger.error(f"Error loading brands: {str(e)}\n{traceback.format_exc()}")
            raise

    def initialize_name_variants(self):
        """Initialize dictionary of name variants"""
        try:
            variants = {
                "inverleven": ["leven", "inver"],
                "old pulteney": ["pulteney", "pult"],
                "glasgow distillery": ["glasgow distillery company", "glasgow"],
                "few spirits": ["few"],
                "isle of harris distillery": ["hearach"],
                "nc'nean distillery": ["nc'nean"],
                "st. georgeâ€™s (the english whisky co.)": ["st. georgeâ€™s", "the english whisky co.", "the english whisky company"],
                "springbank (hazelburn)": ["hazelburn"],
                "isle of arran": ["arran"],
                "braeval (braes of glenlivet)": ["braeval", "braes of glenlivet"],
                "miltonduff (mosstowie)": ["miltonduff", "mosstowie"],
                "glenburgie (glencraig)": ["glenburgie", "glencraig"],
                "glenury / glenury royal": ["glenury", "glenury royal"],
                "tobermory": ["ledaig"],
                "bruichladdich": ["port charlotte", "octomore", "laddie"],
                "laphroaig": ["frog"],
                "royal brackla": ["brackla"],
                "royal lochnagar": ["lochnagar"],
                "springbank (longrow)": ["longrow"],
                "knockdhu (ancnoc)": ["knockdhu", "ancnoc"],
                "cooley (unpeated)": ["cooley"],
                "cooley / connemara (peated)": ["connemara"],
                "breuckelen distilling": ["breuckelen"],
                "copperworks distilling Co.": ["copperworks"],
                "high coast distillery": ["high coast"],
                "smÃ¶gen whisky ab": ["smogen"],
                "west cork distillers": ["west cork"],
                "mosgaard whisky": ["mosgaard"],
                "milk & honey distillery": ["milk & honey", "milk and honey"],
                "distillerie de warenghem": ["warenghem", "armorik"],
                "mars shinshu": ["shinshu"],
                "mars tsunuki:": ["tsunuki"],
                "nc'nean distillery": ["nc'nean"],
                "woodinville whiskey co.": ["woodinville"],
                "finger lakes distilling": ["finger lakes"],
                "new york distilling co.": ["new york distilling", "perry's tot", "new york"],
                "peerless distillery": ["peerless"],
                "kyrÃ¶ distillery": ["kyro"],
                "journeyman distillery": ["journeyman"],
                "heaven hill distillery": ["heaven hill"],
                "demerara distillers (el dorado)": ["demerara", "el dorado"],
                "trinidad distillers (angostura)": ["trinidad", "angostura"],
                "compaÃ±ia licorera de nicaragua (flor de caÃ±a)": ["flor de caÃ±a"],
                "varela hermanos (ron abuelo)": ["ron abuelo"],
                "j. goudoulin (veuve goudoulin)": ["goudoulin"],
                "the borders distillery": ["borders", "the borders"],
                "holyrood distillery": ["holyrood"],
                "Isle of Raasay Distillery": ["Raasay"]
                
                # Add more variants as needed
            }
            
            # Create reverse lookup for all variants
            for main_name, variant_list in variants.items():
                for variant in variant_list:
                    self.name_variants[variant.lower()] = main_name
                # Also add the main name as its own variant
                self.name_variants[main_name.lower()] = main_name
        except Exception as e:
            logger.error(f"Error initializing name variants: {e}")

    def find_distillery(self, name):
        """
        Find the distillery by name, using exact match, name variants, or fuzzy matching.

        Args:
            name (str): The name of the distillery to search for.

        Returns:
            tuple: A tuple containing the standardized distillery name and a list of SMWS codes,
                   or (None, None) if no match is found.
        """
        logger.debug(f"🔍 Searching for distillery: {name}")
        
        name_lower = name.lower()
        
        # First check name variants
        if name_lower in self.name_variants:
            standardized_name = self.name_variants[name_lower]
            if standardized_name.lower() in self.distillery_codes:
                return standardized_name.lower(), list(self.distillery_codes[standardized_name.lower()])
        
        # Then check direct matches in distillery_codes
        if name_lower in self.distillery_codes:
            return name_lower, list(self.distillery_codes[name_lower])
        
        # Finally, fall back to fuzzy matching only if no exact matches found
        all_names = list(self.distillery_codes.keys())
        suggestions = get_close_matches(name_lower, all_names, n=1, cutoff=0.6)
        
        if suggestions:
            closest_match = suggestions[0]
            return closest_match, list(self.distillery_codes[closest_match])
        
        return None, None

    @app_commands.command(name="smws", description="Look up a whisky brand by its SMWS number")
    async def smws(self, interaction: discord.Interaction, code: str):
        try:
            logger.debug(f"SMWS command called with code: {code}")
            
            # Defer FIRST, before any file operations
            try:
                await interaction.response.defer()
                logger.debug("Successfully deferred interaction")
            except discord.errors.NotFound:
                logger.warning(f"Interaction expired before defer for code: {code}")
                return
                
            try:
                # Load the original JSON data to check IDs
                with open('data/brands.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"Successfully loaded brands.json")
            except FileNotFoundError:
                logger.error("brands.json file not found")
                await interaction.followup.send(
                    "Configuration file not found. Please contact the bot administrator.",
                    ephemeral=True
                )
                return
            except json.JSONDecodeError:
                logger.error("Error decoding brands.json")
                await interaction.followup.send(
                    "Error reading configuration. Please contact the bot administrator.",
                    ephemeral=True
                )
                return
                
            # Normalize input code (remove spaces, convert to uppercase for consistency)
            lookup_code = code.strip().upper()
            logger.debug(f"Normalized lookup code: {lookup_code}")
            
            # Find the brand by ID, comparing in a case-insensitive way for alphanumeric IDs
            brand = next((brand for brand in data['brands'] 
                        if str(brand['id']).upper() == lookup_code), None)
            
            if not brand:
                logger.debug(f"No brand found for code: {lookup_code}")
                await interaction.followup.send(
                    f"No distillery found with ID {code}",
                    ephemeral=True
                )
                return
            
            logger.debug(f"Found brand: {brand['name']}")
            
            try:
                embed = discord.Embed(
                    title=f"SMWS Code {code}",
                    description=brand['name'],
                    color=discord.Color.blue()
                )
                
                # Handle potential missing or invalid fields
                if 'region' in brand and brand['region']:
                    embed.add_field(name="Region", value=brand['region'], inline=True)
                
                if 'style' in brand and brand['style']:
                    embed.add_field(name="Style", value=brand['style'], inline=True)
                
                if 'details' in brand and isinstance(brand['details'], dict):
                    if 'description' in brand['details'] and brand['details']['description']:
                        # Truncate description if it's too long
                        description = brand['details']['description']
                        if len(description) > 1024:
                            description = description[:1021] + "..."
                        embed.add_field(
                            name="Description",
                            value=description,
                            inline=False
                        )
                    
                    if 'notes' in brand['details'] and brand['details']['notes']:
                        # Truncate notes if they're too long
                        notes = brand['details']['notes']
                        if len(notes) > 1024:
                            notes = notes[:1021] + "..."
                        embed.add_field(
                            name="Notes",
                            value=notes,
                            inline=False
                        )
                
                if 'codes' in brand and isinstance(brand['codes'], (list, set)):
                    other_codes = [str(c) for c in brand['codes'] if str(c).upper() != lookup_code]
                    if other_codes:
                        # Join codes with proper handling for potential non-string values
                        embed.add_field(
                            name="Other SMWS Codes",
                            value=", ".join(other_codes[:25]),  # Limit number of codes shown
                            inline=False
                        )
                
                logger.debug("Successfully created embed")
                
                # Verify embed is valid before sending
                if len(embed) > 6000:  # Discord's embed limit
                    logger.warning("Embed exceeds Discord's size limit")
                    await interaction.followup.send(
                        "The response is too large. Please contact the bot administrator.",
                        ephemeral=True
                    )
                    return
                
                await interaction.followup.send(embed=embed)
                logger.debug("Successfully sent embed response")
                
            except discord.errors.HTTPException as http_err:
                logger.error(f"HTTP error while sending embed: {http_err}")
                await interaction.followup.send(
                    "There was an error displaying the results. Please try again later.",
                    ephemeral=True
                )
            except Exception as embed_err:
                logger.error(f"Error creating/sending embed: {str(embed_err)}\n{traceback.format_exc()}")
                await interaction.followup.send(
                    "There was an error formatting the results. Please try again later.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error in SMWS command: {str(e)}\n{traceback.format_exc()}")
            try:
                await interaction.followup.send(
                    "An error occurred while processing your request.",
                    ephemeral=True
                )
            except discord.errors.NotFound:
                logger.warning("Could not send error message - interaction expired")

    @app_commands.command(name="distillery", description="Look up all SMWS codes for a distillery")
    async def distillery(self, interaction: discord.Interaction, name: str):
        try:
            logger.debug(f"Distillery command called with name: {name}")
            await interaction.response.defer()
            
            distillery_name, codes = self.find_distillery(name)
            
            if not distillery_name or not codes:
                all_names = list(self.distillery_codes.keys())
                suggestions = get_close_matches(name.lower(), all_names, n=3, cutoff=0.5)
                
                if suggestions:
                    suggest_text = "Did you mean one of these?\n" + "\n".join(
                        s.title() for s in suggestions
                    )
                    await interaction.followup.send(
                        f"No exact match found for '{name}'\n\n{suggest_text}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"No SMWS codes found for distillery '{name}'",
                        ephemeral=True
                    )
                return

            embed = discord.Embed(
                title=f"Distillery: {distillery_name.title()}",
                color=discord.Color.blue()
            )

            # Get information from each code's entry
            # Load the original JSON data to get complete entries
            with open('data/brands.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Find all entries that match our codes
            entries = [brand for brand in data['brands'] if str(brand['id']) in codes]
            
            # Add basic info from first entry
            first_entry = entries[0]
            if 'region' in first_entry:
                embed.add_field(name="Region", value=first_entry['region'], inline=True)
            if 'style' in first_entry:
                embed.add_field(name="Style", value=first_entry['style'], inline=True)

            # Add a field showing all related codes
            embed.add_field(
                name="SMWS Codes",
                value=", ".join(sorted(codes)),
                inline=False
            )

            # Add each unique description
            for entry in entries:
                if 'details' in entry and 'description' in entry['details']:
                    code = str(entry['id'])
                    embed.add_field(
                        name=f"Details for code {code}",
                        value=entry['details']['description'],
                        inline=False
                    )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in distillery command: {str(e)}\n{traceback.format_exc()}")
            await interaction.followup.send(
                "An error occurred while processing your request.",
                ephemeral=True
            )

    @app_commands.command(
        name="moreinfo",
        description="Get detailed information about a distillery"
    )
    @app_commands.describe(
        name="Enter the distillery name (e.g., Highland Park, Glenfarclas)"
    )
    async def moreinfo(self, interaction: discord.Interaction, name: str):
        try:
            logger.debug(f"moreinfo command called with name: {name}")
            await interaction.response.defer(thinking=True)  # Defer the response to prevent interaction timeout
            
            # First try to find the correct distillery name using our enhanced search
            distillery_name, _ = self.find_distillery(name)
            if not distillery_name:
                await interaction.followup.send(
                    f"No information found for {name}",
                    ephemeral=True
                )
                return

            # Load and check the moreinfo data
            with open('data/moreinfo.json', 'r') as f:
                details = json.load(f)
            
            info = details.get(distillery_name.lower())
            
            if not info:
                await interaction.followup.send(
                    f"No additional information found for {distillery_name}",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"{distillery_name.title()}",
                color=discord.Color.blue()
            )
            
            for key, value in info.items():
                field_name = key.replace('_', ' ').title()
                embed.add_field(name=field_name, value=value, inline=False)

            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in moreinfo command: {e}")
            await interaction.followup.send(
                "An error occurred while fetching information.",
                ephemeral=True
            )

    @app_commands.command(
        name="permissions",
        description="Show the bot's current permissions on this server"
    )
    async def show_permissions(self, interaction: discord.Interaction):
        try:
            logger.debug(f"permissions command called with name: {interaction.user.name}")
            await interaction.response.defer(thinking=True)  # Defer the response
            
            bot_member = interaction.guild.get_member(interaction.client.user.id)
            if not bot_member:
                await interaction.followup.send("Could not fetch bot permissions.", ephemeral=True)
                return

            permissions = bot_member.guild_permissions
        
            embed = discord.Embed(
                title=f"Bot Permissions in {interaction.guild.name}",
                color=discord.Color.blue()
            )

            enabled = []
            disabled = []
            for perm, value in permissions:
                if value:
                    enabled.append(f"✅ {perm}")
                else:
                    disabled.append(f"❌ {perm}")

            if enabled:
                embed.add_field(
                    name="Enabled Permissions",
                    value="\n".join(enabled),
                    inline=False
                )
            if disabled:
                embed.add_field(
                    name="Disabled Permissions",
                    value="\n".join(disabled),
                    inline=False
                )

            # Use followup instead of response since we deferred
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in permissions command: {e}")
            await interaction.followup.send(
                "An error occurred while fetching permissions.",
                ephemeral=True
            )
            
    @app_commands.command(
        name="help",
        description="Display help information about SMWS bot commands"
    )
    async def help_command(self, interaction: discord.Interaction):
        """Display help information about SMWS bot commands"""
        try:
            logger.debug(f"Help command called with name: {interaction.user.name}")
            await interaction.response.defer(thinking=True)  # Add this line to prevent timeout
            
            embed = discord.Embed(
                title="SMWS Bot Help",
                description="How to use the SMWS Bot",
                color=discord.Color.green()
            )
            embed.add_field(
                name="/smws <code>",
                value="Look up a distillery by its SMWS code\nExamples:\n`/smws 1` or `/smws G1` or `/smws R3`",
                inline=False
            )
            embed.add_field(
                name="/distillery <name>",
                value="Look up the SMWS code for a distillery\nExample: `/distillery Highland Park`",
                inline=False
            )
            embed.add_field(
                name="Available Formats",
                value="Distillery Codes: Various formats (23, 56, G1, R3, etc.)",
                inline=False
            )
            embed.add_field(
                name="More Info",
                value="Check if Whiskord has additional info about a Distillery or Independent Bottler",
                inline=False
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await interaction.followup.send(
                "An error occurred while displaying help.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(BrandCommands(bot))
    logger.info("BrandCommands cog loaded")