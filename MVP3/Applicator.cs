using System.Text.Json;

namespace Mvp3;

public static class Applicator
{
    public static SparseDctModel LoadModel(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException("Model file was not found.", path);
        SparseDctModel model = JsonSerializer.Deserialize<SparseDctModel>(File.ReadAllText(path))
            ?? throw new InvalidDataException("Model JSON was empty.");
        if (model.Format != "sparse-orthonormal-dct-2d-v1" || model.Width != 260 || model.Height != 310)
            throw new InvalidDataException("Unsupported or invalid model.");
        if (model.Coefficients.Count == 0 || model.Coefficients.Count >= model.Width * model.Height)
            throw new InvalidDataException("Model is not sparse.");
        return model;
    }

    public static ImageData Apply(string inputPath, SparseDctModel model, bool allowResize)
    {
        ImageData source = ImageIo.Load(inputPath);
        return Apply(source, model, allowResize);
    }

    public static ImageData Apply(ImageData source, SparseDctModel model, bool allowResize)
    {
        if (source.Width != model.Width || source.Height != model.Height)
        {
            if (!allowResize)
                throw new InvalidDataException($"Input is {source.Width}x{source.Height}; expected " +
                    $"{model.Width}x{model.Height}. Pass --resize to resize explicitly.");
            source = ImageIo.Resize(source, model.Width, model.Height);
        }

        byte[] learned = DctModel.ReconstructBytes(model);
        byte[] output = new byte[source.Pixels.Length];
        for (int p = 0; p < learned.Length; p++)
        {
            int i = p * 4;
            byte a = learned[p];
            if (a >= model.ContentThreshold)
            {
                output[i] = source.Pixels[i];
                output[i + 1] = source.Pixels[i + 1];
                output[i + 2] = source.Pixels[i + 2];
                output[i + 3] = (byte)((source.Pixels[i + 3] * a + 127) / 255);
            }
            else
            {
                output[i] = output[i + 1] = output[i + 2] = 0;
                output[i + 3] = a;
            }
        }
        return new ImageData(model.Width, model.Height, output);
    }
}
