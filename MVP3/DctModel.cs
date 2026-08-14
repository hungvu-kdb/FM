namespace Mvp3;

public static class DctModel
{
    public static double[] Forward(double[] input, int width, int height)
    {
        if (input.Length != width * height)
            throw new ArgumentException("DCT input size does not match dimensions.");
        var cosX = CosineTable(width);
        var cosY = CosineTable(height);
        var scaleX = Scales(width);
        var scaleY = Scales(height);
        var horizontal = new double[input.Length];
        var coefficients = new double[input.Length];

        for (int y = 0; y < height; y++)
        {
            int row = y * width;
            for (int u = 0; u < width; u++)
            {
                double sum = 0;
                int basis = u * width;
                for (int x = 0; x < width; x++)
                    sum += input[row + x] * cosX[basis + x];
                horizontal[row + u] = sum * scaleX[u];
            }
        }

        for (int v = 0; v < height; v++)
        {
            int basis = v * height;
            for (int u = 0; u < width; u++)
            {
                double sum = 0;
                for (int y = 0; y < height; y++)
                    sum += horizontal[y * width + u] * cosY[basis + y];
                coefficients[v * width + u] = sum * scaleY[v];
            }
        }
        return coefficients;
    }

    public static double[] Inverse(double[] coefficients, int width, int height)
    {
        if (coefficients.Length != width * height)
            throw new ArgumentException("DCT coefficient size does not match dimensions.");
        var cosX = CosineTable(width);
        var cosY = CosineTable(height);
        var scaleX = Scales(width);
        var scaleY = Scales(height);
        var vertical = new double[coefficients.Length];
        var output = new double[coefficients.Length];
