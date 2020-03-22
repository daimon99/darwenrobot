var img1 = "static/PlayStation-DualShock-4.jpg"

window.onload = function () {
    var canvas = document.getElementById("c1")
    ctx = canvas.getContext('2d')
    width = ctx.canvas.width
    height = ctx.canvas.height
    ctx.imageSmoothingEnabled = false
    img1 = new Image()
    img1.src = "static/PlayStation-DualShock-4.jpg"
    img1.height = height
    img1.width = width

    img1.onload = function () {
        ctx.drawImage(img1, 0, 0, width, height)
    }
    console.log(ctx)
}
