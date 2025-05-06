# Phaser Tutorial

## The Basic Structure
```
javascriptCopyconst config = { ... };
const game = new Phaser.Game(config);
```
This creates a new Phaser game instance with your configuration settings.

**Configuration Object**
```
javascriptCopyconst config = {
    type: Phaser.AUTO,             // Lets Phaser choose WebGL or Canvas depending on browser support
    width: 800,                    // Game width in pixels
    height: 600,                   // Game height in pixels
    physics: {                     // Physics engine settings
        default: "arcade",         // Using the simple Arcade Physics engine
        arcade: {
            gravity: { y: 200 },   // Gravity pulls objects down at 200 pixels/second²
        },
    },
    scene: {                       // The game scene
        preload: preload,          // Function to call for loading assets
        create: create,            // Function to call once all assets are loaded
    },
};
```

## Game Functions
**Preload Function**
```
javascriptCopyfunction preload() {
    this.load.setBaseURL("https://labs.phaser.io");  // Base URL for all assets
    // Load images from the server into memory, giving each a reference name
    this.load.image("sky", "assets/skies/space3.png");
    this.load.image("plane", "assets/sprites/ww2plane.png");
    this.load.image("green", "assets/particles/green.png");
    this.load.image("astroid", "assets/games/asteroids/asteroid1.png");
    this.load.image("astroid2", "assets/games/asteroids/asteroid1.png");
    this.load.image("astroid3", "assets/games/asteroids/asteroid1.png");
}
```
This function loads all your game assets (images, sounds, etc.) before the game starts. The this keyword refers to the current scene.

## Create Function
```
javascriptCopyfunction create() {
    // Add background and asteroid images at specific coordinates
    this.add.image(400, 300, "sky");         // Center of the 800x600 canvas
    this.add.image(700, 300, "astroid");     // Right side
    this.add.image(100, 200, "astroid2");    // Left side
    this.add.image(400, 40, "astroid3");     // Top

    // Create particle effect
    const particles = this.add.particles("green");   // Use the green image as particle
    const emitter = particles.createEmitter({
        speed: 100,                      // Particle movement speed
        scale: { start: 1, end: 0 },     // Particles shrink as they move
        blendMode: "ADD",                // Makes particles glow
    });

    // Add a plane sprite with physics
    const plane = this.physics.add.image(400, 100, "plane");
    plane.setVelocity(100, 200);             // Initial velocity (x, y)
    plane.setBounce(1, 1);                   // Perfect bounce on collision (1.0 = no energy loss)
    plane.setCollideWorldBounds(true);       // Plane will bounce off the edges of the screen
    emitter.startFollow(plane);              // Particles follow the plane
}
```
This function creates your game world after all assets are loaded. It:

Adds the space background and asteroid images
Creates a particle effect with the green image
Creates a plane sprite with physics properties
Makes the plane bounce around the screen
Attaches the particle emitter to the plane


## What's Happening In Your Game

The game sets up an 800x600 pixel canvas
The background shows a space scene
Three asteroids are placed around the screen (static images)
A plane is added that:

Moves with an initial velocity
Bounces perfectly off the edges of the screen
Has a glowing green particle trail following behind it


The plane will continue to bounce around indefinitely due to the physics settings

To modify the map, you would typically replace the static background and asteroid images with a tilemap created in Tiled Map Editor, then load that map into Phaser using the Tilemap API.


# Integrating a Tilemap with Your Existing Phaser Code
I'll walk you through the process of integrating a tilemap created with Tiled Map Editor into your existing Phaser game. This will replace your current static background and asteroid images with a more flexible and dynamic tilemap system.

