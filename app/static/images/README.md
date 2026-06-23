Place these project image files here:

- `logo.jpg` - your league logo. It is used in the header and rotating loading screen.
- `home.jpg` - the football player/home-page image used on the Team Admin public home page.

The database seed stores these public URLs in `app_assets`:

- `league_logo` -> `/static/images/logo.jpg`
- `home_hero_photo` -> `/static/images/home.jpg`

You can replace either image file without changing the templates. If you host images in Supabase Storage later, update the matching `app_assets.url` value to the Supabase public URL.
