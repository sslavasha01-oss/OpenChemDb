import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.Properties;

import com.actelion.research.chem.IDCodeParser;
import com.actelion.research.chem.StereoMolecule;
import com.actelion.research.chem.MolfileCreator;

public class App {

    static {
        java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"));
        System.setProperty("user.timezone", "UTC");
    }

    private static final String DB_URL = "jdbc:postgresql://localhost:5433/archive_db";
    private static final String USER = "chemist";
    private static final String PASSWORD = "archive_pass";

    public static void main(String[] args) {
        System.out.println("=== STARTING CLEAN LINEAR RESTORATION ===");

        Properties props = new Properties();
        props.setProperty("user", USER);
        props.setProperty("password", PASSWORD);
        props.setProperty("options", "-c timezone=UTC");

        String selectQuery = "SELECT id, idcode, id_coords_2d FROM book_base " +
                "WHERE id > ? AND idcode IS NOT NULL AND id_coords_2d IS NOT NULL " +
                "ORDER BY id ASC LIMIT ?;";

        String updateQuery = "UPDATE book_base SET mol_file = ?::mol WHERE id = ?;";

        int batchSize = 5000;
        long totalProcessed = 0;
        long lastId = -1;

        IDCodeParser parser = new IDCodeParser();

        try (Connection conn = DriverManager.getConnection(DB_URL, props);
             PreparedStatement selectStmt = conn.prepareStatement(selectQuery);
             PreparedStatement updateStmt = conn.prepareStatement(updateQuery)) {

            conn.setAutoCommit(false);

            boolean hasMore = true;
            while (hasMore) {
                selectStmt.setLong(1, lastId);
                selectStmt.setInt(2, batchSize);

                try (ResultSet rs = selectStmt.executeQuery()) {
                    int rowsInBatch = 0;
                    boolean foundAnyRows = false;

                    while (rs.next()) {
                        foundAnyRows = true;
                        long id = rs.getLong("id");
                        lastId = id;

                        String idcode = rs.getString("idcode");
                        String idCoords2D = rs.getString("id_coords_2d");

                        if (idcode == null || idcode.isEmpty()) continue;

                        try {
                            StereoMolecule mol = new StereoMolecule();
                            parser.parse(mol, idcode, idCoords2D);

                            MolfileCreator creator = new MolfileCreator(mol);
                            String molfileContent = creator.getMolfile();

                            if (molfileContent == null || molfileContent.trim().isEmpty()) continue;

                            // ГЛАВНОЕ ИСПРАВЛЕНИЕ: вычищаем неразрывные пробелы (NBSP)
                            // и на всякий случай возвраты каретки, оставляя чистый ASCII-текст
                            String cleanMolfile = molfileContent
                                    .replace('\u00A0', ' ')
                                    .replace("\r\n", "\n");

                            updateStmt.setString(1, cleanMolfile);
                            updateStmt.setLong(2, id);
                            updateStmt.addBatch();

                            rowsInBatch++;
                        } catch (Exception e) {
                            System.err.println("Error creating molfile for ID " + id + ": " + e.getMessage());
                        }
                    }

                    if (!foundAnyRows) {
                        System.out.println("[INFO] Reached the end of the table. Finishing processing.");
                        hasMore = false;
                        break;
                    }

                    if (rowsInBatch > 0) {
                        updateStmt.executeBatch();
                    }

                    // Всегда коммитим шаг батча, продвигая транзакцию вперед
                    conn.commit();

                    totalProcessed += rowsInBatch;
                    System.out.println("Processed up to ID: " + lastId + ". Total records updated: " + totalProcessed);

                } catch (Exception e) {
                    conn.rollback();
                    System.err.println("Batch failed around ID " + lastId + ", rolling back batch. Error: " + e.getMessage());
                    // Шагаем через один ID, чтобы гарантированно не зависнуть, если попалась критически битая структура
                    lastId++;
                }
            }

            System.out.println("\n--- Done! ---");
            System.out.println("Processing finished successfully. Total structures restored: " + totalProcessed);

        } catch (Exception e) {
            System.err.println("Database error occurred: " + e.getMessage());
            e.printStackTrace();
        }
    }
}