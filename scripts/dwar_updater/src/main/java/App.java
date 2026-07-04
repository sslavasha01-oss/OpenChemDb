import java.sql.*;
import java.util.Properties;

import com.actelion.research.chem.IDCodeParser;
import com.actelion.research.chem.StereoMolecule;
import com.actelion.research.chem.MolfileCreator;

public class App {

    private static final String DB_URL = "jdbc:postgresql://localhost:5433/archive_db";
    private static final String USER = "chemist";
    private static final String PASSWORD = "archive_pass";

    static {
        java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"));
        System.setProperty("user.timezone", "UTC");
    }

    public static void main(String[] args) {
        System.out.println("=== STARTING MOL_FILE COLUMN UPDATE ===");

        Properties props = new Properties();
        props.setProperty("user", USER);
        props.setProperty("password", PASSWORD);

        IDCodeParser parser = new IDCodeParser();

        // Берем только те строки, где есть idcode, но mol_file еще не заполнен
        String selectQuery = "SELECT id, idcode, id_coords_2d FROM public.book_base WHERE idcode IS NOT NULL AND mol_file IS NULL;";
        String updateQuery = "UPDATE public.book_base SET mol_file = public.mol_from_ctab(?::cstring) WHERE id = ?;";

        try (Connection conn = DriverManager.getConnection(DB_URL, props);
             PreparedStatement selectStmt = conn.prepareStatement(selectQuery);
             PreparedStatement updateStmt = conn.prepareStatement(updateQuery);
             ResultSet rs = selectStmt.executeQuery()) {

            // Отключаем автокоммит для пакетного выполнения апдейтов
            conn.setAutoCommit(false);

            int count = 0;
            int batchSize = 1000;

            while (rs.next()) {
                int id = rs.getInt("id");
                String idcode = rs.getString("idcode");
                String coords = rs.getString("id_coords_2d");

                if (idcode.trim().isEmpty()) continue;

                try {
                    // Генерируем мольфайл из Actelion IDCode
                    StereoMolecule mol = new StereoMolecule();
                    parser.parse(mol, idcode, coords);
                    MolfileCreator creator = new MolfileCreator(mol);
                    String rawMolfile = creator.getMolfile();

                    // Подставляем параметры: 1 — строка мольфайла, 2 — ID для WHERE
                    updateStmt.setString(1, rawMolfile);
                    updateStmt.setInt(2, id);
                    updateStmt.addBatch();

                    count++;

                    // Отправляем пачку в базу каждые 1000 записей
                    if (count % batchSize == 0) {
                        updateStmt.executeBatch();
                        conn.commit();
                        System.out.println("Обновлено строк: " + count);
                    }

                } catch (Exception e) {
                    System.err.println("[SKIP] Ошибка генерации структуры для ID " + id + ": " + e.getMessage());
                }
            }

            // Сбрасываем остатки
            if (count % batchSize != 0) {
                updateStmt.executeBatch();
                conn.commit();
            }

            System.out.println("\n=== ОБНОВЛЕНИЕ ЗАВЕРШЕНО! Всего заполнено ячеек mol_file: " + count + " ===");

        } catch (SQLException e) {
            System.err.println("\n[CRITICAL SQL ERROR] Сбой при выполнении пакета обновлений. Откат изменений.");
            e.printStackTrace();

            SQLException nextEx = e.getNextException();
            while (nextEx != null) {
                System.err.println("Детали ошибки базы: " + nextEx.getMessage());
                nextEx = nextEx.getNextException();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}