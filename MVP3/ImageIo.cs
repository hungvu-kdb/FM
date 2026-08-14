using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Mvp3;

public static class ImageIo
{
    public static ImageData Load(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException("PNG input was not found.", path);

        using var stream = File.OpenRead(path);
        var decoder = new PngBitmapDecoder(stream, BitmapCreateOptions.PreservePixelFormat,
            BitmapCacheOption.OnLoad);
        if (decoder.Frames.Count != 1)
            throw new InvalidDataException("Expected a single-frame PNG.");

        BitmapSource source = decoder.Frames[0];
        if (source.Format != PixelFormats.Bgra32)
            source = new FormatConvertedBitmap(source, PixelFormats.Bgra32, null, 0);

        int stride = checked(source.PixelWidth * 4);
        byte[] pixels = new byte[checked(stride * source.PixelHeight)];
        source.CopyPixels(pixels, stride, 0);
        return new ImageData(source.PixelWidth, source.PixelHeight, pixels);
    }

    public static ImageData Resize(ImageData source, int width, int height)
    {
        BitmapSource bitmap = BitmapSource.Create(source.Width, source.Height, 96, 96,
            PixelFormats.Bgra32, null, source.Pixels, source.Width * 4);
        var transformed = new TransformedBitmap(bitmap,
            new System.Windows.Media.ScaleTransform((double)width / source.Width,
                (double)height / source.Height));
        BitmapSource converted = transformed.Format == PixelFormats.Bgra32
            ? transformed
            : new FormatConvertedBitmap(transformed, PixelFormats.Bgra32, null, 0);
        if (converted.PixelWidth != width || converted.PixelHeight != height)
            throw new InvalidOperationException("WPF resize produced unexpected dimensions.");
        byte[] pixels = new byte[checked(width * height * 4)];
        converted.CopyPixels(pixels, width * 4, 0);
        return new ImageData(width, height, pixels);
    }
